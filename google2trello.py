#Google Docs' Spreadsheet -> Trello import script
#(ideal for Google's forms)
#by Grissess

__version__=(0, 0, 2)

import time

print 'Google2Trello version', __version__
print 'The time is', time.ctime()
##raise SystemError('Simulated Error Condition')

import ConfigParser

from trollop import TrelloConnection
from google_spreadsheet.api import SpreadsheetAPI
from gdata.service import BadAuthentication
from requests.exceptions import HTTPError

def safename(s):
	ret=''
	for c in s:
		if c.isalnum():
			ret+=c
	return ret.lower()

cp=ConfigParser.RawConfigParser()
try:
	cp.readfp(open('g2t.cfg', 'r'))
except IOError:
	print 'Could not find g2t.cfg file; aborting.'
	exit()

try:
	descfmt=open(cp.get('Transfer', 'formatfile'), 'r').read()
	custfmts={}
	destlists={}
	skipsets={}
	custnames={}
	for opt in cp.options('Transfer'):
		if opt.startswith('format_'):
			x, col, val=opt.split('_')
			custfmts.setdefault(col, {})[val]=open(cp.get('Transfer', opt), 'r').read()
			print 'Assigned custom format for value', val, 'in column', col, 'to', cp.get('Transfer', opt)
		if opt.startswith('list_'):
			x, col, val=opt.split('_')
			destlists.setdefault(col, {})[val]=cp.get('Transfer', opt)
			print 'Assigned custom list for value', val, 'in column', col, 'to', cp.get('Transfer', opt)
		if opt.startswith('skip_'):
			x, col, val=opt.split('_')
			skipsets.setdefault(col, set()).add(val)
			print 'Assigned skip condition for value', val, 'in column', col
		if opt.startswith('name_'):
			x, col, val=opt.split('_')
			custnames.setdefault(col, {})[val]=cp.get('Transfer', opt)
			print 'Assigned custom name for value', val, 'in column', col, 'to', cp.get('Transfer', opt)
except IOError:
	print 'Could not find one or more formats; aborting.'
	exit()
	
print 'Dispatchers:'
print '\tCustom formats:', custfmts
print '\tDestination lists:', destlists
print '\tSkip sets:', skipsets
print '\tCustom names:', custnames

api=SpreadsheetAPI(cp.get('Google', 'user'), cp.get('Google', 'password'), 'python.google2trello')
print 'Authenticating against Google...'
try:
	ss=api.list_spreadsheets()
except BadAuthentication:
	print 'Could not authenticate with specified Google credentials.'
	import traceback
	traceback.print_exc()
	exit()

sname=cp.get('Google', 'spreadsheet')
for entry in ss:
	if entry[0]==sname:
		spreadsheet=entry[1]
		break
else:
	print 'Could not find spreadsheet', sname
	print 'Possible choices:', ss
	exit()

ws=api.list_worksheets(spreadsheet)
sname=cp.get('Google', 'sheet')
for entry in ws:
	if entry[0]==sname:
		sheet=entry[1]
		break
else:
	print 'Could not find spreadsheet', sname
	print 'Possible choices:', ws
	exit()
	
print 'Retrieving spreadsheet...'
sheet=api.get_worksheet(spreadsheet, sheet)
print 'Spreadsheet retrieved.'

con=TrelloConnection(cp.get('Trello', 'key'), cp.get('Trello', 'token'))
print 'Authenticating against Trello...'
try:
	me=con.me
except HTTPError:
	print 'Could not authenticate with specified Trello credentials.'
	exit()

boards=me.boards
bname=cp.get('Trello', 'board')
for b in boards:
	if b.name==bname:
		board=b
		break
else:
	print 'Could not find board', bname
	print 'Possible choices:', [i.name for i in me.boards]
	exit()
	
lists=board.lists
lname=cp.get('Trello', 'list')
for l in lists:
	if l.name==lname:
		list_=l
		break
else:
	print 'Could not find list', lname
	print 'Possible choices:', [i.name for i in board.lists]
	exit()

print 'Retrieving cards...'
starttime=time.time()
cards=board.cards
endtime=time.time()
dtime=endtime-starttime
cnames=[card.name for card in cards]
print 'Retrieved', len(cards), 'cards in', dtime, 'seconds.'

print 'Retrieving rows...'
starttime=time.time()
rows=sheet.get_rows()
endtime=time.time()
dtime=endtime-starttime
print 'Retrieved', len(rows), 'rows in', dtime, 'seconds.'

namefmt=cp.get('Transfer', 'name')

fake=(cp.get('Transfer', 'fake').lower()=='true')
verbose=(cp.get('Transfer', 'verbose').lower()=='true')

seennames=set()

if not rows:
	print 'No rows! Stop.'
	exit()

print 'Sample row:', rows[0]

for row in rows:
	name=namefmt%row
	for col in row.iterkeys():
		if col in custnames:
			if safename(row[col]) in custnames[col]:
				name=custnames[col][safename(row[col])]%row
				print 'Using custom name for', col, '=', safename(row[col])
	if name in seennames:
		print 'WARNING: Potential duplicate spreadsheet entry:', repr(name)
		i=2
		orgname = name
		while ('%s (#%d)'%(orgname, i)) in seennames:
			i+=1
		name = '%s (#%d)'%(orgname, i)
		print '...renamed to:', repr(name)
	else:
		seennames.add(name)
	if name in cnames:
		print 'Skipping', repr(name), '--the card exists'
		continue
	fmt=descfmt
	dest=list_
	skip=False
	for col in row.iterkeys():
	    if col in skipsets and skipsets[col]==safename(row[col]):
	        skip=True
	        print 'Skipping', repr(name), 'on a skip condition'
	        break
	    if col in custfmts:
			if safename(row[col]) in custfmts[col]:
				fmt=custfmts[col][safename(row[col])]
				print 'Using custom format for', col, '=', safename(row[col])
	    if col in destlists:
			if safename(row[col]) in destlists[col]:
				lname=destlists[col][safename(row[col])]
				print 'Using custom list for', col, '=', safename(row[col])
				for l in board.lists:
					if l.name==lname:
						dest=l
						break
				else:
					raise NameError('ERROR: No such list')
	if verbose:
		print ' Built card '.center(40, '=')
		print name
		print '-'*len(name)
		print fmt%row
		print '='*40
	if skip or fake:
	    print 'Not adding card -- skipped or running in fake mode'
	    continue
	dest.add_card(name, fmt%row)
	cnames.append(name)
	print 'Added card', repr(name)

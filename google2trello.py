#Google Docs' Spreadsheet -> Trello import script
#(ideal for Google's forms)
#by Grissess

__version__=(0, 0, 1)

print 'Google2Trello version', __version__
##raise SystemError('Simulated Error Condition')

import time
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

cp=ConfigParser.SafeConfigParser()
try:
	cp.readfp(open('g2t.cfg', 'r'))
except IOError:
	print 'Could not find g2t.cfg file; aborting.'
	exit()

try:
	descfmt=open(cp.get('Transfer', 'formatfile'), 'r').read()
	custfmts={}
	destlists={}
	for opt in cp.options('Transfer'):
		if opt.startswith('format_'):
			x, col, val=opt.split('_')
			if col not in custfmts:
				custfmts[col]={}
			custfmts[col][val]=open(cp.get('Transfer', opt), 'r').read()
			print 'Assigned custom format for value', val, 'in column', col, 'to', cp.get('Transfer', opt)
		if opt.startswith('list_'):
			x, col, val=opt.split('_')
			if col not in destlists:
				destlists[col]={}
			destlists[col][val]=cp.get('Transfer', opt)
			print 'Assigned custom list for value', val, 'in column', col, 'to', cp.get('Transfer', opt)
except IOError:
	print 'Could not find one or more formats; aborting.'
	exit()
	
print 'Dispatchers:'
print 'Custom formats:', custfmts
print 'Destination lists:', destlists

api=SpreadsheetAPI(cp.get('Google', 'user'), cp.get('Google', 'password'), 'python.google2trello')
print 'Authenticating against Google...'
try:
	ss=api.list_spreadsheets()
except BadAuthentication:
	print 'Could not authenticate with specified Google credentials.'
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

seennames=set()

for row in rows:
	name=namefmt%row
	if name in seennames:
		print 'WARNING: Potential duplicate spreadsheet entry:', repr(name)
	else:
		seennames.add(name)
	if name in cnames:
		print 'Skipping',repr(name), '--the card exists'
		continue
	fmt=descfmt
	dest=list_
	for col in row.iterkeys():
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
					print 'ERROR: No such list.'
					exit()
	dest.add_card(row[nameattr], fmt%row)
	print 'Added card', repr(name)

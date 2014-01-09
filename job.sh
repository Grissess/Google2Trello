python google2trello.py 1>G2T_LOG 2>G2T_ERROR
[ -s G2T_ERROR ] && cat email.txt G2T_LOG G2T_ERROR | sendmail -vt 2>&1 > MAIL_LOG

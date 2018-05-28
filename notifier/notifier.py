import smtplib
from email.mime.text import MIMEText
from itertools import groupby
from urllib.parse import urljoin, urlencode
import requests
from jinja2 import Template
from settings import *


### Constants

ERR_CANNOT_RETRIEVE_ISSUES = 'Can not retrieve issues from Jira. Response is %s %s.'

### Classes

class Issue:
    def __init__(self, info):
        self.info = info

    key = property(lambda self: self.info['key'])
    type = property(lambda self: self.info['fields']['issuetype']['name'])
    status = property(lambda self: self.info['fields']['status']['name'])
    summary = property(lambda self: self.info['fields']['summary'])
    assignee = property(lambda self: Assignee(self.info['fields']['assignee']))

    def __str__(self):
        return '%s %s' % (self.key, self.summary)

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        return self.key == other.key


class Assignee:
    def __init__(self, info):
        self.info = info

    key = property(lambda self: self.info['key'])
    name = property(lambda self: self.info['displayName'])
    email = property(lambda self: self.info['emailAddress'])

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        return self.key == other.key

### Handling

def retrieve_issues():
    url = urljoin(JIRA_URL, 'rest/api/latest/search')
    resp = requests.get(url, auth=(JIRA_USERNAME, JIRA_PASSWORD), params={'jql': JIRA_QUERY})

    if not resp.ok:
        print(ERR_CANNOT_RETRIEVE_ISSUES % (resp.status_code, resp.reason))
        exit(1)

    return list(map(Issue, resp.json()['issues']))


def notify_assignee(assignee, issues):
    text = Template(EMAIL_BODY).render(
        BROWSE_URL=urljoin(JIRA_URL, 'browse'), ISSUES_URL=urljoin(JIRA_URL, 'issues'),
        assignee=assignee, issues=issues,
        JQL=urlencode({'jql': JIRA_QUERY + ' AND assignee=currentUser()'}))
    recipient = '%s <%s>' % (assignee.name, assignee.email)
    msg = MIMEText(text, EMAIL_TYPE)
    msg['From'] = EMAIL_FROM
    msg['To'] = recipient
    msg['Subject'] = Template(EMAIL_SUBJECT).render(assignee=assignee, issues=issues)
    smtp = smtplib.SMTP(SMTP_SERVER)
    smtp.sendmail(EMAIL_FROM, [recipient], msg.as_string())
    smtp.quit()


def main():
    issues = retrieve_issues()
    for assignee, issues in groupby(issues, Issue.assignee.fget):
        notify_assignee(assignee, list(issues))


if __name__ == "__main__":
    main()

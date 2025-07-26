#!/usr/bin/env python3

import re
import json
import os
from datetime import datetime
from itertools import chain
from urllib.request import Request, urlopen
from dotenv import load_dotenv 

load_dotenv()

token = os.getenv("GITHUB_TOKEN") or os.getenv("TOKEN")

if not token:
    raise RuntimeError("Missing GitHub token. Set GITHUB_TOKEN or TOKEN.")

def repo_alias(repo_name):
    return repo_name.replace("-", "_").replace(".", "_")

created = [
    ("banflam", "from-afar"),
    ("banflam", "chess-trainer"),
    ("banflam", "chess-thoughts"),
    ("banflam", "path-pledge"),
    ("banflam", "credit-captain"),
    ("banflam", "regular-show"),
]

maintain = [
    #("couchers-org", "couchers"),
]

query = """
{
  issues: search(type: ISSUE, query: "author:banflam is:issue") {
    issueCount
  }

  prs: search(type: ISSUE, query: "author:banflam is:pr") {
    issueCount
  }

  user(login: "banflam") {
    followers { totalCount }
    following { totalCount }
    gists { totalCount }
    issues { totalCount }
    pullRequests { totalCount }
    repositories(first: 100, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        forkCount
        languages(first: 100) {
          edges {
            node { name }
            size
          }
        }
        stargazerCount
        viewerPermission
      }
    }
    repositoriesContributedTo(privacy: PUBLIC) {
      totalCount
    }
  }
"""

for owner, repo in chain(created, maintain):
    alias = repo_alias(repo)
    query += f"""
  {alias}: repository(owner: "{owner}", name: "{repo}") {{
    description
    stargazerCount
  }}
"""

query += "}"

commits = json.load(
    urlopen(
        Request(
            "https://api.github.com/search/commits?q=author:banflam&per_page=1",
            headers={"Accept": "application/vnd.github.cloak-preview"},
        )
    )
)["total_count"]

data = json.load(
    urlopen(
        Request(
            "https://api.github.com/graphql",
            json.dumps({"query": query}).encode("ascii"),
            {"Authorization": f"token {token}"},
        )
    )
)

forks = 0
langs = {}
size = 0
stars = 0

user = data["data"].get("user")
if user is None:
    raise RuntimeError("GitHub API did not return user info — check your token permissions.")

for repo in user["repositories"]["nodes"]:
    if repo["viewerPermission"] != "ADMIN":
        continue

    forks += repo["forkCount"]
    stars += repo["stargazerCount"]
    for lang in repo["languages"]["edges"]:
        size += lang["size"]
        name = lang["node"]["name"]
        langs[name] = langs.get(name, 0) + lang["size"]

regex = re.compile(r"^(.*?)\s*\[maintainer[^\]]+\]\s*$")

def add_repos(repos):
    global data
    global readme
    global regex

    for owner, repo in sorted(
        repos,
        key=lambda x: int(
            data["data"][repo_alias(x[1])]["stargazerCount"]
        ),
        reverse=True,
    ):
        repo_data = data["data"][repo_alias(repo)]
        description = repo_data["description"]

        if owner == "nix-community":
            description = regex.sub(r"\1", description)

        readme += f"- [**{repo}**](https://github.com/{owner}/{repo}) (⭐ {repo_data['stargazerCount']}) - {description}\n"

readme = "https://rishi.ag/\n\nSoftware Engineer Living in New York City"
readme += "\n\n#### Projects I created\n\n"
add_repos(created)
#readme += "\n#### Projects I help maintain\n\n"
#add_repos(maintain)

readme += f"""
<table>
  <tr align="center">
    <td><b>Statistics</b></td>
    <td><b>Languages</b></td>
  </tr>
  <tr valign="top">
    <td><table>
      <tr>
        <td>Repositories</td>
        <td><a href="https://github.com/banflam?tab=repositories">
          {user["repositories"]["totalCount"]}
        </a></td>
      </tr>
      <tr>
        <td>Gists</td>
        <td><a href="https://gist.github.com/banflam">
          {user["gists"]["totalCount"]}
        </a></td>
      </tr>
      <tr>
        <td>Stargazers</td>
        <td>{stars}</td>
      </tr>
      <tr>
        <td>Forks</td>
        <td>{forks}</td>
      </tr>
      <tr>
        <td>Contributed to</td>
        <td>{user["repositoriesContributedTo"]["totalCount"]}</td>
      </tr>
      <tr>
        <td>Commits</td>
        <td>{commits}</td>
      </tr>
      <tr>
        <td>Issues</td>
        <td>{data["data"]["issues"]["issueCount"]}</td>
      </tr>
      <tr>
        <td>Pull requests</td>
        <td>{data["data"]["prs"]["issueCount"]}</td>
      </tr>
      <tr>
        <td>Followers</td>
        <td><a href="https://github.com/banflam?tab=followers">
          {user["followers"]["totalCount"]}
        </a></td>
      </tr>
      <tr>
        <td>Following</td>
        <td><a href="https://github.com/banflam?tab=following">
          {user["following"]["totalCount"]}
        </a></td>
      </tr>
    </table></td>
    <td><table>"""

for k, v in sorted(langs.items(), key=lambda x: x[1], reverse=True)[:10]:
    readme += f"<tr><td>{k}</td><td>{round(v / size * 100, 2)}%</td></tr>"

readme += f"""</table></td>
  </tr>
</table>

<sub>Last updated: {datetime.utcnow().strftime("%F %T")} UTC</sub>
"""

open("README.md", "w").write(readme)

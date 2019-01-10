"""
Watch CI and report results back to upstream.
"""
import logging

import github

from onegittorulethemall.services.pagure import PagureService


logger = logging.getLogger(__name__)
# FIXME: create a global config and move this data in there
package_mapping = {
    "python-docker": {
        "source-git": "TomasTomecek/docker-py-source-git"
    }
}


class Holyrood:
    """ such a good gin """

    def __init__(self, github_token, pagure_user_token):
        self.pagure_token = pagure_user_token
        self.github_token = github_token
        self.g = github.Github(login_or_token=self.github_token)

    def process_pr(self, msg):
        """
        Process flags from the PR and update source git PR with those flags
        :param msg:
        :return:
        """
        project_name = msg["msg"]["pullrequest"]["project"]["name"]

        ps = PagureService(token=self.pagure_token)
        project = ps.get_project(repo=project_name, namespace="rpms")

        try:
            logger.info("new flag for PR for %s", project_name)
            source_git = package_mapping[project_name]["source-git"]
        except KeyError:
            logger.info("source git not found")
            return
        pr_id = msg["msg"]["pullrequest"]["id"]

        # find info for the matching source git pr
        sg_pr_id = project.get_sg_pr_id(pr_id)

        # check the commit which tests were running for
        commit = project.get_sg_top_commit(pr_id)

        if not (sg_pr_id and commit):
            logger.info("this doesn't seem to be a source-git related event")
            return

        repo = self.g.get_repo(source_git)
        sg_pull = repo.get_pull(sg_pr_id)
        for c in sg_pull.get_commits():
            if c.sha == commit:
                gh_commit = c
                break
        else:
            raise RuntimeError("commit was not found in source git")

        # Pagure states match github states, coolzies
        # https://developer.github.com/v3/repos/statuses/#create-a-status
        gh_commit.create_status(
            msg["msg"]["flag"]["status"],
            target_url=msg["msg"]["flag"]["url"],
            description=msg["msg"]["flag"]["comment"],
            context=msg["msg"]["flag"]["username"],  # simple-koji-ci or Fedora CI
        )
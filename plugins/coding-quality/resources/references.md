# References

External sources behind the rules in this repo.

## AWS / GitLab OIDC

- IAM condition keys for workload identity federation:
  https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_iam-condition-keys.html#condition-keys-wif
- GitLab ID token authentication (claim list):
  https://docs.gitlab.com/ci/secrets/id_token_authentication/
- Update a role trust policy:
  https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_update-role-trust-policy.html#id_roles_update-trust-policy-console
- AWS Support: https://aws.amazon.com/support

> Source advisory: AWS IAM security notification — GitLab.com path-based `sub` claims are
> reclaimable; pin `namespace_id`/`project_id`. Captured in [GitLab CI overlay](../stacks/gitlab-ci.md).

## Practice

- Conventional Commits: https://www.conventionalcommits.org/
- RFC 2119 (MUST/SHOULD/MAY): https://www.rfc-editor.org/rfc/rfc2119
- OWASP Top Ten: https://owasp.org/www-project-top-ten/
- GDPR overview: https://gdpr.eu/

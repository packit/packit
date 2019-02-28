# Tests

We use [Tox](https://pypi.org/project/tox), configuration is in [tox.ini](../tox.ini)

Running tests locally:

```
make prepare-check && make check
```

Running tests in a container is currently broken, PRs are welcome.
```
make build-tests && make test-in-container
```

As a CI we use [CentOS CI](https://ci.centos.org/job/packit-pr/) with a configuration in [Jenkinsfile](../Jenkinsfile)

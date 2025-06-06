# MerossIOT REST

[![GitHubPackage][GitHubPackageBadge]][GitHubPackageLink]
[![DockerPublishing][DockerPublishingBadge]][DockerLink]
[![DockerSize][DockerSizeBadge]][DockerLink]
[![DockerPulls][DockerPullsBadge]][DockerLink]

RESTed (Flask with Waitress) example of [MerosIot](https://github.com/albertogeniola/MerossIot) library.

Starts a Meross Manager infinite loop that executes operations received from REST endpoints on available devices.

- Right now only:
  - `mss620` device supported.
  - `on`, `off`, `toggle` operations supported.
- Secrets taken from Docker secrets (`get-docker-secret` lib).

[GitHubPackageBadge]: https://github.com/malpiszon/meross_iot_rest/actions/workflows/build_and_push.yml/badge.svg
[GitHubPackageLink]: https://github.com/malpiszon/meross_iot_rest/pkgs/container/meross_iot_rest
[DockerPublishingBadge]: https://github.com/malpiszon/meross_iot_rest/actions/workflows/build_and_push.yml/badge.svg
[DockerPullsBadge]: https://badgen.net/docker/pulls/malpiszon/meross_iot_rest?icon=docker&label=Docker+Pulls&labelColor=black&color=green
[DockerSizeBadge]: https://badgen.net/docker/size/malpiszon/meross_iot_rest?icon=docker&label=Docker+Size&labelColor=black&color=green
[DockerLink]: https://hub.docker.com/r/malpiszon/meross_iot_rest

## Hestia - take care of the hearth of you discord server

## Features

- Schedule the creation of server events

## Setting up the server

### Running with docker

1. Copy the .env.example into .env and fill with the needed information
1. Create the docker image (remember the dot when you use this command)
    ```
    docker build -t hestia .
    ```
1. Run the docker image
    ```
    docker run --env-file=.env hestia:latest
    ```

## Contributing

### Installing dependencies

[Install python](https://docs.python-guide.org/starting/installation/), we are
on version 3.11
We use pipenv to manage our dependencies if you don't have it you can
install it by using:
    ```
    pip install pipenv
    ```
Then install the required packages, and configure the environment by using:
    ```
    pipenv install --dev
    ```

### Running on local machine

You can use docker and follow the instructions above or you can:

1. Copy the .env.example into .env and fill with the needed information
1. Run
    ```
    pipenv run python -m hestia.main
    ```

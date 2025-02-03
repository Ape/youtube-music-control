#!/usr/bin/env python3

import argparse
import json
import requests


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter):
    def _get_help_string(self, action):
        # Do not show default values for these arguments
        if action.dest in ["endpoint", "data", "list", "verbose"]:
            return action.help

        return super()._get_help_string(action)


class API:
    def __init__(self, server, api):
        self.server = server.rstrip("/")
        self.api = api.rstrip("/")

    def authenticate(self, username):
        auth_url = f"{self.server}/auth/{username}"
        response = requests.post(auth_url)

        if response.status_code != 200:
            print(f"Request failed: {response.status_code} {response.reason}")
            print(auth_url)
            return None

        return response.json().get("accessToken")

    def fetch_api_doc(self, verbose=False):
        doc_url = f"{self.server}/doc"
        response = requests.get(doc_url)

        if verbose:
            print(f"GET {doc_url} {response.status_code}")
            if response.status_code == 200 and response.text.strip():
                try:
                    data = response.json()
                    print(json.dumps(data, indent=2))
                except Exception:
                    print(response.text)

        if response.status_code != 200:
            print(f"Request failed: {response.status_code} {response.reason}")
            print(doc_url)
            return {}

        api_doc = response.json()
        paths = api_doc.get("paths", {})
        endpoints = {}

        for path, methods in paths.items():
            if not path.startswith(self.api):
                continue

            if path.endswith("-info"):
                continue

            endpoint = path[len(self.api):]

            if endpoint.startswith("/"):
                endpoint = endpoint[1:]

            if endpoint not in endpoints:
                endpoints[endpoint] = {}

            for method, details in methods.items():
                method_upper = method.upper()
                description = details.get("description", endpoint)
                data = None
                schema = None

                if method_upper == "POST" and "requestBody" in details:
                    req_body = details.get("requestBody", {})
                    data = req_body.get("description", "no description")
                    content = req_body.get("content", {})

                    if "application/json" in content:
                        schema = content["application/json"].get("schema", {})

                endpoints[endpoint][method_upper] = {
                    "description": description,
                    "data": data,
                    "schema": schema,
                }

        return endpoints

    def make_request(self, token, endpoint, http_method,
                     verbose=False, post_data=None):
        url = f"{self.server}{self.api}/{endpoint}"
        headers = {"Authorization": f"Bearer {token}"}

        if verbose:
            if http_method == "POST" and post_data is not None:
                try:
                    print(json.dumps(post_data, indent=2))
                except Exception:
                    print(post_data)

        response = requests.request(
            http_method,
            url,
            headers=headers,
            json=post_data,
        )

        if not response.ok:
            print(f"Request failed: {response.status_code} {response.reason}")
            print(url)
            return

        parsed_data = None
        if response.text.strip():
            try:
                parsed_data = response.json()
            except ValueError:
                parsed_data = response.text.strip()

        if verbose:
            print(f"{http_method} {url} {response.status_code}")

            if parsed_data:
                if isinstance(parsed_data, dict):
                    print(json.dumps(parsed_data, indent=2))
                else:
                    print(parsed_data)
        else:
            if response.status_code == 200 and parsed_data:
                if isinstance(parsed_data, dict):
                    print(json.dumps(parsed_data, indent=2))
                else:
                    print(parsed_data)


def main():
    parser = argparse.ArgumentParser(
        description="Remote control client for th-ch/youtube-music",
        formatter_class=CustomFormatter
    )

    parser.add_argument("--server", "-s", default="http://localhost:26538",
                        help="Server base URL")
    parser.add_argument("--api", default="/api/v1",
                        help="API path")
    parser.add_argument("--user", "-u", default="youtube-music-control",
                        help="Username for authentication")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List available API endpoints")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print request details")
    parser.add_argument("endpoint", nargs="?",
                        help="API endpoint to call")
    parser.add_argument("data", nargs="?",
                        help="Data for POST requests: JSON or a single value")

    args = parser.parse_args()
    api = API(args.server, args.api)

    if args.list:
        endpoints = api.fetch_api_doc(verbose=args.verbose)

        if not endpoints:
            print("No endpoints found!")
            return

        print("Available API endpoints:")

        for ep, methods in endpoints.items():
            lines = f"  {ep}"

            for method, details in methods.items():
                description = details.get("description")
                data = details.get("data")

                if len(methods) == 1:
                    lines += f": {description}"
                else:
                    lines += f"\n    {method}: {description}"

                if method == "POST" and data:
                    lines += f" (data: {data})"

            print(lines)

        return

    if not args.endpoint:
        parser.print_help()
        return

    endpoints = api.fetch_api_doc(verbose=False)

    if args.data is not None:
        http_method = "POST"
    else:
        if args.endpoint in endpoints:
            methods = endpoints[args.endpoint]
            if "GET" in methods:
                http_method = "GET"
            else:
                http_method = list(methods.keys())[0]
        else:
            http_method = "POST" if args.data is not None else "GET"

    post_data = None

    if http_method == "POST" and args.data is not None:
        try:
            loaded = json.loads(args.data)
        except json.JSONDecodeError:
            loaded = args.data

        if not isinstance(loaded, dict):
            try:
                schema = endpoints[args.endpoint]["POST"].get("schema")
            except KeyError:
                print(f"No POST data schema for {args.endpoint}")
                return

            if schema and schema.get("type") == "object":
                properties = schema.get("properties", {})
                required = schema.get("required", [])

                if len(required) == 1:
                    key = required[0]

                    if properties[key]["type"] == "number":
                        try:
                            value = float(loaded)

                            if value.is_integer():
                                value = int(value)

                            loaded = value
                        except Exception:
                            pass

                    loaded = {key: loaded}

        post_data = loaded

    token = api.authenticate(args.user)

    if token:
        api.make_request(
            token,
            args.endpoint,
            http_method,
            verbose=args.verbose,
            post_data=post_data
        )


if __name__ == "__main__":
    main()

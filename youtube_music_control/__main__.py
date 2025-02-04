import argparse
import json

import requests


class API:
    def __init__(self, server, api):
        self.server = server.rstrip("/")
        self.api = api.rstrip("/")

    def authenticate(self, username, verbose=False):
        url = f"{self.server}/auth/{username}"
        response = requests.post(url)

        if response.status_code != 200:
            print(f"Request failed: {response.status_code} {response.reason}")
            print(url)
            return None

        if verbose:
            print(f"POST {url} {response.status_code}")

        return response.json().get("accessToken")

    def fetch_api_doc(self, verbose=False, print_data=False):
        url = f"{self.server}/doc"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Request failed: {response.status_code} {response.reason}")
            print(url)
            return {}

        if verbose:
            print(f"GET {url} {response.status_code}")

        if print_data:
            if response.status_code == 200 and response.text.strip():
                try:
                    data = response.json()
                    print(json.dumps(data, indent=2))
                except Exception:
                    print(response.text)

        api_doc = response.json()
        endpoints = {}
        paths = api_doc.get("paths", {})

        for path, methods in paths.items():
            if not path.startswith(self.api):
                continue

            if path.endswith("-info"):
                continue

            endpoint = path[len(self.api):].lstrip("/")

            if endpoint not in endpoints:
                endpoints[endpoint] = {}

            for method, details in methods.items():
                method = method.upper()
                description = details.get("description", endpoint)
                data = None
                schema = None

                if method in {"POST", "PATCH"} and "requestBody" in details:
                    req_body = details["requestBody"]
                    data = req_body.get("description", "no description")
                    content = req_body.get("content", {})

                    if "application/json" in content:
                        schema = content["application/json"].get("schema", {})

                endpoints[endpoint][method] = {
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
            if http_method in ("POST", "PATCH") and post_data is not None:
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


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Remote control client for th-ch/youtube-music",
    )

    parser.add_argument("--server", "-s", default="http://localhost:26538",
                        help="Server base URL (default: %(default)s)")
    parser.add_argument("--api", default="/api/v1",
                        help="API path (default: %(default)s)")
    parser.add_argument("--user", "-u", default="youtube-music-control",
                        help="Username for authentication"
                             " (default: %(default)s)")
    parser.add_argument("--patch", action="store_true",
                        help="Use PATCH method")
    parser.add_argument("--delete", action="store_true",
                        help="Use DELETE method")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List available API endpoints")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print request details")
    parser.add_argument("endpoint", nargs="?",
                        help="API endpoint to call")
    parser.add_argument("data", nargs="?",
                        help="Request data: JSON or a single value")

    args = parser.parse_args()

    if args.delete and args.patch:
        parser.error(
            "Cannot specify both --delete and --patch options simultaneously."
        )

    return parser, args


def display_endpoints(endpoints):
    if not endpoints:
        print("No endpoints found!")
        return

    print("Available API endpoints:")
    for endpoint, methods in endpoints.items():
        line = f"  {endpoint}"

        for method, details in methods.items():
            description = details.get("description")
            data_info = details.get("data")

            if len(methods) == 1:
                line += f": {description}"
            else:
                line += f"\n    {method}: {description}"

            if method in ("POST", "PATCH") and data_info:
                line += f" (data: {data_info})"

        print(line)


def determine_http_method(args, endpoints):
    if args.delete:
        return "DELETE"

    if args.patch:
        return "PATCH"

    if args.data is not None:
        return "POST"

    if args.endpoint not in endpoints:
        return "GET"

    methods = endpoints[args.endpoint]

    if "GET" in methods:
        return "GET"

    return list(methods.keys())[0]


def process_post_data(http_method, args, endpoints):
    if http_method not in ("POST", "PATCH"):
        return None

    if args.data is None:
        return None

    try:
        loaded = json.loads(args.data)
    except json.JSONDecodeError:
        loaded = args.data

    if isinstance(loaded, dict):
        return loaded

    endpoint_doc = endpoints.get(args.endpoint, {})
    schema = endpoint_doc.get(http_method, {}).get("schema")

    if schema is None:
        print(f"No {http_method} data schema for {args.endpoint}")
        return None

    if schema.get("type") != "object":
        return loaded

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    if len(required) != 1:
        print(f"{args.endpoint} {http_method} requires an object")
        return None

    key = required[0]

    if properties.get(key, {}).get("type") == "number":
        try:
            value = float(loaded)

            if value.is_integer():
                value = int(value)

            loaded = value
        except Exception:
            pass

    return {key: loaded}


def main():
    parser, args = parse_arguments()
    api = API(args.server, args.api)

    if args.list:
        endpoints = api.fetch_api_doc(args.verbose, print_data=args.verbose)
        display_endpoints(endpoints)
        return

    if not args.endpoint:
        parser.print_help()
        return

    endpoints = api.fetch_api_doc(args.verbose, print_data=False)
    http_method = determine_http_method(args, endpoints)
    post_data = process_post_data(http_method, args, endpoints)

    token = api.authenticate(args.user, args.verbose)

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

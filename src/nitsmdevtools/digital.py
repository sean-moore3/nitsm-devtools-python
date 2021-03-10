import re


def site_list_to_site_numbers(site_list: str):
    sites = re.split(r"\s*,\s*", site_list)
    site_numbers = [int(re.match(r"site(\d+)", site).group(1)) for site in sites]
    return site_numbers, sites


def channel_list_to_pins(channel_list: str):
    channels = re.split(r"\s*,\s*", channel_list)
    sites = [-1] * len(channels)
    pins = channels[:]
    for i in range(len(channels)):
        try:
            site, pins[i] = re.split(r"[/\\]", channels[i])
        except ValueError:
            pass
        else:
            sites[i] = int(re.match(r"site(\d+)", site).group(1))
    return channels, pins, sites


if __name__ == "__main__":
    site_list = "0, 1, 2"
    print(site_list_to_site_numbers(site_list))
    channel_list = "0,1,2"
    print(channel_list_to_pins(channel_list))

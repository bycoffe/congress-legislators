 #!/usr/bin/env python

# gets ICPSR ID for every member

# options:
#  --cache: load from cache if present on disk (default: true)
#  --bioguide: load only one legislator, by his/her bioguide ID
#  --congress: do *only* updates for legislators serving in specific congress

import utils
from utils import load_data, save_data, parse_date
import string
import csv
import unicodedata

def run():

    # default to caching
    cache = utils.flags().get('cache', True)
    force = not cache


    only_bioguide = utils.flags().get('bioguide', None)
    congress = utils.flags().get('congress',None)


    data_files = []

    print("Loading %s..." % "legislators-current.yaml")
    legislators = load_data("legislators-current.yaml")
    data_files.append((legislators,"legislators-current.yaml"))
    print("Loading %s..." % "legislators-historical.yaml")
    legislators = load_data("legislators-historical.yaml")
    data_files.append((legislators,"legislators-historical.yaml"))

    if congress == None:
        raise Exception("the --congress flag is required")

    # load roll call data
    url = "https://voteview.polisci.ucla.edu/static/data/csv/member/member_both_%s.csv" % congress
    destination = "icpsr/source/member_both_%s.csv" % congress
    data = [x for x in csv.DictReader(utils.download(url, destination, force).splitlines())]

    error_log = csv.writer(open("cache/errors/mismatch/mismatch_%s.csv" % congress, "w"))
    error_log.writerow(["error_type","matches","icpsr_name","icpsr_state","is_territory","old_id","new_id"])

    for data_file in data_files:
        for legislator in data_file[0]:
            num_matches = 0
            # # this can't run unless we've already collected a bioguide for this person
            bioguide = legislator["id"].get("bioguide", None)
            # if we've limited this to just one bioguide, skip over everyone else
            if only_bioguide and (bioguide != only_bioguide):
                continue

            chamber = legislator['terms'][len(legislator['terms'])-1]['type']

            #only run for selected congress
            latest_congress = utils.congress_from_legislative_year(utils.legislative_year(parse_date(legislator['terms'][len(legislator['terms'])-1]['start'])))
            if chamber == "sen":
                congresses = [latest_congress,latest_congress+1,latest_congress+2]
                chamber_name = "Senate"
                district = '0'
            else:
                congresses = [latest_congress]
                chamber_name = "House"
                district = str(legislator['terms'][len(legislator['terms'])-1]['district'])
                # Voteview uses 1 for at-large but legislators-*.yaml uses 0
                if district == '0':
                    district = '1'

            if int(congress) not in congresses:
                continue

            # pull data to match from yaml
            last_name_unicode = legislator['name']['last'].upper().strip().replace('\'','')
            last_name = unicodedata.normalize('NFD', str(last_name_unicode)).encode('ascii', 'ignore')
            #state = utils.states[legislator['terms'][len(legislator['terms'])-1]['state']].upper()[:7].strip()
            state = legislator['terms'][len(legislator['terms'])-1]['state']

            # select icpsr source data based on more recent chamber
            write_id = ""
            for line in data:
                vv_lastname = unicodedata.normalize('NFD', str(line['bioname'].split(',')[0].lower())).encode('ascii', 'ignore')
                if vv_lastname == last_name.lower() and line['state_abbrev'] == state and chamber_name == line['chamber'] and district == line['district_code']:
                    num_matches += 1
                    write_id = int(line['icpsr'])

            #skip if icpsr id is currently in data
            if "icpsr" in legislator["id"]:
                if write_id == legislator["id"]["icpsr"] or write_id == "":
                    continue
                elif write_id != legislator["id"]["icpsr"] and write_id != "":
                    error_log.writerow(["Incorrect_ID","NA",last_name[:8],state,"NA",legislator["id"]["icpsr"],write_id])
                    print("ID updated for %s" % last_name)

            if num_matches == 1:
                legislator['id']['icpsr'] = int(write_id)
            else:
                if state == 'GUAM' or state == 'PUERTO' or state == "VIRGIN" or state == "DISTRIC" or state == "AMERICA" or state == "NORTHER" or state == "PHILIPP":
                    error_log.writerow(["Non_1_match_number",str(num_matches),last_name[:8],state,"Y","NA","NA"])
                else:
                    print("%s matches found for %s, %s in congress %s" % (num_matches,
                                                                          last_name[:8],
                                                                          state,
                                                                          congress))
                    error_log.writerow(["Non_1_match_number",str(num_matches),last_name,state,"N","NA","NA"])

        save_data(data_file[0], data_file[1])

    ## the following three lines can be run as a separate script to update icpsr id's for all historical congresses
    # import os

    # for i in range(1,114):
    #     os.system("python ICPSR_id.py --congress=" + str(i))

if __name__ == '__main__':
  run()

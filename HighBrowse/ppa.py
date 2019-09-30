import json
import socket
import ssl
import argparse


def run():
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--fields", help="Fields to return from PanelApp response")
    args = parser.parse_args()

    # validate fields
    fields = args.fields
    field_confirm = ''
    if fields is None:
        field_confirm = '(Reporting default fields EVIDENCE, PHENOTYPES, and MODE_OF_INHERITANCE)'
        fields = ['evidence', 'phenotypes', 'mode_of_inheritance']
    else:
        fields = fields.split(',')
        field_confirm = '(Reporting for entered fields: {})'.format(fields)
        known_fields = ['gene_data', 'entity_type', 'entity_name', 'confidence_level', 'penetrance', 'mode_of_pathogenicity',
                        'publications', 'evidence', 'phenotypes', 'mode_of_inheritance', 'tags', 'panel']
        for field in fields:
            if field not in known_fields:
                print('Invalid field specified. Fields must be one of the following: ', known_fields)
                return

    # compose gene list
    gene_list = []
    for line in sys.stdin:
        gene_list.append(line.split()[0])
    if len(gene_list) == 0:
        print("Did not receive any genes. Please try again.")
        return
    else:
        # perform request
        header, body = request('GET', 'panelapp.genomicsengland.co.uk', 443, '/api/v1/genes/', gene_list)
        py_obj = json.loads(body)
        results = py_obj.get('results', None)
        if not results or len(results) == 0:
            print('JSON response did not contain results field or results is empty')
            return

        # format and print response
        first_result = results[0]
        gene_name = first_result.get("entity_name", None)
        print("\n* PANEL APP RESULTS for gene {} has {} entries:".format(gene_name, len(results)))
        print('* {}'.format(field_confirm))
        print("-------------------------------------------------------------------------------")
        out = []
        for result in results:
            for field in fields:
                value = result.get(field, [])
                curr_str = ''
                if field in ['publications, evidence, phenotypes', 'tags']:
                    for curr_val in value:
                        curr_str += ', ' + curr_val
                    curr_str = json.dumps(curr_str[2:])
                    if curr_str == '':
                        curr_str = '-'
                else:
                    curr_str = value
                    if curr_str == '':
                        curr_str = '-'
                out.append(curr_str)
        for i in range(len(out)):
            label = fields[i % len(fields)].upper()
            val = out[i]
            print('{}: {}'.format(label, val))
            if ((i + 1) % len(fields)) == 0:
                print("-------------------------------------------------------------------------------")


# performs secure request over TSL socket
def request(method, host, port, path, gene_list):
    # format request
    for gene in gene_list:
        case_gene = gene.upper()
        path += case_gene + ', '
    path = path[0:len(path)-2]
    path += '/'

    # open socket and send request
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ws = context.wrap_socket(s, server_hostname=host)
    ws.connect((host, port))
    ws.sendall("{} {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n".format(method, path, host).encode("utf8"))
    response = ws.makefile("rb").read().decode("utf8")
    ws.close()

    # verify and parse result
    head, body = response.split("\r\n\r\n", 1)
    lines = head.split("\r\n")
    version, status, explanation = lines[0].split(" ", 2)
    assert status == "200", "Something went wrong with contacting PanelApp - server error {}: {}".format(status, explanation)
    headers = {}
    for line in lines[1:]:
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    return headers, body


# get the show on the road
if __name__ == "__main__":
    import sys
    run()

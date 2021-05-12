import sys
# these are mandatory
if len(sys.argv) >= 5:
    client = sys.argv[1]
    type = sys.argv[2]
    asset = sys.argv[3]
    volume = sys.argv[4]
else:
    sys.exit("Error! Include arguments: client_num, order_type, asset, volume, price(optional), mes(optional)")
# these are optional
if len(sys.argv) >= 6:
    price = sys.argv[5]
else:
    price = 0
if len(sys.argv) >= 7:
    mes = sys.argv[6]
else:
    mes = 0

order_string = "{},{},{},{},{}".format(type, asset, price, volume, mes)
file_name = './data/client_order_'+client+'.dat'

f=open(file_name, 'w')
f.write(order_string)
f.close()

print("Wrote {} to file {}.".format(order_string, file_name))

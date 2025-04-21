# tab_to_xml.py
import csv
from lxml import etree


def convert_tab_to_xml(tab_path, xml_path):
    root = etree.Element("OMW")

    with open(tab_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        header = next(reader)  # 跳过标题行

        for row in reader:
            synset = etree.SubElement(root, "Synset")
            etree.SubElement(synset, "ID").text = row[0]
            etree.SubElement(synset, "Lemma").text = row[1]
            etree.SubElement(synset, "Definition").text = row[2]

    tree = etree.ElementTree(root)
    tree.write(xml_path, pretty_print=True, encoding='utf-8')


if __name__ == "__main__":
    convert_tab_to_xml("wn-wcmn.tab", "wn-cmn.xml")
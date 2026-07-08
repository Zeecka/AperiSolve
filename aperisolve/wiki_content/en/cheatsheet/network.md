Title: Network & PCAP Forensics Cheatsheet - tshark, USB, DNS Exfil
Description: A copy-paste command checklist for network-capture CTFs: triage with capinfos and tshark, extract files and HTTP objects, decode USB keyboard/mouse HID, and spot DNS/ICMP exfiltration, ordered most-common first.
NavTitle: Network / PCAP
Order: 50

# Network / PCAP cheatsheet

Command recipes for packet-capture (`.pcap`/`.pcapng`) challenges. Captures often
carry files, credentials, or a payload smuggled in a protocol field.

## Triage {: #triage }

```console
$ capinfos capture.pcap                 # size, packet count, time range
$ tshark -r capture.pcap -q -z io,phs   # protocol hierarchy — what's in here?
$ tshark -r capture.pcap -q -z conv,tcp # TCP conversations (endpoints, bytes)
```

Open in [Wireshark](https://www.wireshark.org/) for interactive work:
*Statistics → Protocol Hierarchy*, then *Follow → TCP/HTTP Stream*.

## Pull out files & strings {: #extract }

```console
$ strings -n 8 capture.pcap | grep -iE 'flag|CTF|pass|user'
$ binwalk -e capture.pcap                          # embedded files in payloads
$ tshark -r capture.pcap --export-objects http,out/   # carve HTTP objects
$ tshark -r capture.pcap --export-objects smb,out/    # SMB / TFTP / IMF too
$ foremost -i capture.pcap -o carved/                 # carve by signature
```

Reassemble a single stream:

```console
$ tshark -r capture.pcap -qz follow,tcp,raw,0 | tr -d '\n' | xxd -r -p > stream0.bin
$ tcpflow -r capture.pcap -o flows/               # one file per direction per flow
```

## Credentials & HTTP {: #http }

```console
$ tshark -r capture.pcap -Y http.request -T fields -e http.host -e http.request.uri
$ tshark -r capture.pcap -Y 'http.authbasic' -T fields -e http.authbasic
$ tshark -r capture.pcap -Y 'ftp.request.command==PASS' -T fields -e ftp.request.arg
```

## USB HID (keyboard / mouse) {: #usb }

USB captures leak keystrokes and mouse movement.

```console
# Keyboard: 8-byte HID reports on usb.capdata
$ tshark -r capture.pcap -Y 'usb.capdata && usb.data_len==8' -T fields -e usb.capdata > keys.txt
```

Map the HID usage IDs to characters with a decoder script (search
"USB keyboard HID CTF decoder"); mouse captures plot movement into an image.

## Covert channels {: #covert }

- **DNS exfil** → long/odd subdomains carrying base32/hex:
  `tshark -r c.pcap -Y 'dns.qry.name' -T fields -e dns.qry.name | sort -u`.
- **ICMP exfil** → data in echo payloads:
  `tshark -r c.pcap -Y 'icmp' -T fields -e data.data`.
- **TLS** → you need the key: set `SSLKEYLOGFILE` / *Wireshark → Preferences →
  TLS → (Pre)-Master-Secret log*, then streams decrypt.

## Wireless {: #wifi }

```console
$ aircrack-ng -w rockyou.txt capture.pcap          # crack a WPA handshake
$ tshark -r capture.pcap -Y eapol                   # confirm a 4-way handshake exists
```

## Related

- Tools: [binwalk](/wiki/tools/binwalk) · [foremost](/wiki/tools/foremost) ·
  [strings](/wiki/tools/strings).
- Files inside the capture: [Files & Archives cheatsheet](/wiki/cheatsheet/files).
- Cracking handshakes/zips: [Brute-force cheatsheet](/wiki/cheatsheet/brute-force).

# PT Git — Packet Tracer changes

## Lab

<pre>.ptgit-action-selftest/lab with spaces.pkt</pre>

<pre>Devices changed: 2
Devices added:   0
Devices removed: 0
Links added:     1
Links removed:   0
Warnings:        0
Lint errors:     0</pre>

<pre>R1
  interface GigabitEthernet0/0
   ip address 192.168.10.1/24
   no shutdown
+ interface GigabitEthernet0/1
+  ip address 10.10.20.1/24
+  no shutdown

SW2
  interface GigabitEthernet0/1
   switchport mode access
-  switchport access vlan 10
+  switchport access vlan 20

Topology
+ R1:GigabitEthernet0/1 &lt;-&gt; SW2:GigabitEthernet0/1 [eStraightThrough]
</pre>

Common IOS credentials are masked; other saved values are included.

# Server Audit

- Audit ID: M10 Agent 06
- Collected: 2026-09-26 16:46–16:47 UTC
- Host: srva
Scope: read-only host inspection from /home/923873155/BeatIT

No credentials, environment variables, GPU UUIDs, process IDs, or container
environment values are recorded here. Listener/process names are limited to
what is needed to identify exposed services.

## Summary

| Area | Observed result |
|---|---|
| CPU | Intel Core i9-10900X, 1 socket, 10 cores / 20 threads; 20 online CPUs |
| RAM | 125 GiB total; 101 GiB available at collection time |
| Swap | 8.0 GiB total; 7.8 GiB used, 251 MiB free |
| GPU | 2 × NVIDIA GeForce RTX 3090; 24,576 MiB VRAM each |
| NVIDIA driver | 535.288.01 |
| CUDA toolkit | nvcc 12.2.91, release 12.2 |
| Root filesystem | 3.6T ext4; 2.8T used, 743G available, 79% used |
| Data filesystem | 2.7T ext4 at /usr/data; 580G used, 2.2T available, 22% used |
| Docker | Client 29.8.1, server 29.5.3; rootless; overlayfs; cgroup v2 |
| Containers | 2 running and healthy: PostgreSQL 16 Alpine and Valkey 7 Alpine |
| Public/wildcard listeners | TCP 22, 5432, 6379, 3459, 4949, 8765, 8766 |

## Host and CPU

Command:

~~~sh
date -u '+%Y-%m-%dT%H:%M:%SZ'
uname -a
sed -n '1,12p' /etc/os-release
lscpu
nproc
~~~

Result:

~~~text
2026-09-26T16:46:27Z
Linux srva 6.8.0-139-generic #139-Ubuntu SMP PREEMPT_DYNAMIC Sat Aug 1 03:52:05 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux
Ubuntu 24.04.5 LTS (Noble Numbat), VERSION_ID=24.04
Architecture: x86_64
CPU(s): 20
On-line CPU(s) list: 0-19
Vendor ID: GenuineIntel
Model name: Intel(R) Core(TM) i9-10900X CPU @ 3.70GHz
Thread(s) per core: 2
Core(s) per socket: 10
Socket(s): 1
NUMA node(s): 1
nproc=20
~~~

## RAM and swap

Command:

~~~sh
free -h
awk '/^(MemTotal|MemAvailable|SwapTotal|SwapFree):/ {print}' /proc/meminfo
~~~

Result:

~~~text
               total        used        free      shared  buff/cache   available
Mem:           125Gi        23Gi       8.0Gi        92Mi        95Gi       101Gi
Swap:          8.0Gi       7.8Gi        251Mi

MemTotal:       131571788 kB
MemAvailable:   106697276 kB
SwapTotal:         8388604 kB
SwapFree:           257420 kB
~~~

Finding: swap is almost full at collection time. Services capable of memory
spikes should be monitored before additional workloads are enabled.

## GPU, VRAM, driver, and CUDA

Command:

~~~sh
nvidia-smi --query-gpu=index,name,driver_version,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu --format=csv,noheader
nvidia-smi -L
nvcc --version
cat /proc/driver/nvidia/version
~~~

Result:

~~~text
0, NVIDIA GeForce RTX 3090, 535.288.01, 24576 MiB, 1 MiB, 24258 MiB, 33, 0 %
1, NVIDIA GeForce RTX 3090, 535.288.01, 24576 MiB, 1 MiB, 24250 MiB, 38, 0 %
GPU 0: NVIDIA GeForce RTX 3090
GPU 1: NVIDIA GeForce RTX 3090

Cuda compilation tools, release 12.2, V12.2.91
NVRM version: NVIDIA UNIX x86_64 Kernel Module 535.288.01
~~~

Host-level GPU access is confirmed and nearly idle in this snapshot: both GPUs
report 24,576 MiB total VRAM, approximately 24,2xx MiB free, and 0%
utilization. This is a point-in-time observation, not a load test.

Container GPU boundary check:

~~~sh
command -v nvidia-container-cli || true
test -e /dev/nvidia0 && ls -l /dev/nvidia* || true
docker info --format 'DefaultRuntime={{.DefaultRuntime}}'
docker info --format 'Runtimes={{json .Runtimes}}'
~~~

Result:

~~~text
nvidia-container-cli: unavailable
/dev/nvidia*: unavailable from this audit shell
DefaultRuntime=runc
Runtimes include runc and io.containerd.runc.v2; no NVIDIA runtime was reported.
~~~

Conclusion: host GPU visibility is confirmed, but NVIDIA device injection into
Docker containers is not confirmed. Do not claim GPU-backed containers are
deployable until an approved NVIDIA Container Toolkit smoke test passes.

## Disk and block devices

Command:

~~~sh
df -hT -x tmpfs -x devtmpfs
lsblk -e7 -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL
~~~

Result:

~~~text
Filesystem                           Type      Size  Used Avail Use% Mounted on
efivarfs                             efivarfs  128K  110K   14K  89% /sys/firmware/efi/efivars
/dev/mapper/ubuntu--vg--1-ubuntu--lv ext4      3.6T  2.8T  743G  79% /
/dev/mapper/data--vg-data--lv        ext4      2.7T  580G  2.2T  22% /usr/data
/dev/sda2                            ext4      2.0G  201M  1.6G  11% /boot
/dev/sda1                            vfat      1.1G  6.2M  1.1G   1% /boot/efi

NAME                           SIZE TYPE FSTYPE      MOUNTPOINTS MODEL
sda                            3.6T disk                         Samsung SSD 870
├─sda1                           1G part vfat        /boot/efi
├─sda2                           2G part ext4        /boot
└─sda3                         3.6T part LVM2_member
  └─ubuntu--vg--1-ubuntu--lv   3.6T lvm  ext4        /
nvme0n1                        1.8T disk                         Samsung SSD 970 EVO Plus 2TB
└─nvme0n1p1                    1.8T part LVM2_member
  └─data--vg-data--lv          2.7T lvm  ext4        /usr/data
nvme1n1                      931.5G disk                         Samsung SSD 970 EVO Plus 1TB
└─nvme1n1p1                  931.5G part LVM2_member
  └─data--vg-data--lv          2.7T lvm  ext4        /usr/data
~~~

Finding: / is at 79% usage and should have a release threshold/alert before
building images or accepting large artifacts. /usr/data has substantial
headroom. The EFI variable filesystem is small and 89% full, but is not an
application data volume.

## Docker

Commands:

~~~sh
docker version --format 'Client={{.Client.Version}} Server={{if .Server}}{{.Server.Version}}{{else}}unavailable{{end}}'
docker context show
docker context inspect --format '{{json .Endpoints.docker.Host}}'
docker info --format 'ServerVersion={{.ServerVersion}}'
docker info --format 'OSType={{.OSType}} Architecture={{.Architecture}} CPUs={{.NCPU}} MemoryBytes={{.MemTotal}}'
docker info --format 'DockerRootDir={{.DockerRootDir}} StorageDriver={{.Driver}} CgroupVersion={{.CgroupVersion}}'
docker info --format 'DefaultRuntime={{.DefaultRuntime}} SecurityOptions={{json .SecurityOptions}}'
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker system df
docker compose version
docker-compose version
~~~

Result:

~~~text
Client=29.8.1 Server=29.5.3
Context=rootless
Endpoint=unix:///home/923873155/.docker/run/docker.sock
OSType=linux Architecture=x86_64 CPUs=20 MemoryBytes=134729510912
DockerRootDir=/home/923873155/.local/share/docker StorageDriver=overlayfs CgroupVersion=2
DefaultRuntime=runc SecurityOptions=seccomp, rootless, cgroupns

NAMES                     IMAGE                    STATUS                  PORTS
ghostrange-postgres-dev   postgres:16-alpine       Up 15 hours (healthy)   0.0.0.0:5432->5432/tcp
ghostrange-valkey-dev     valkey/valkey:7-alpine   Up 15 hours (healthy)   0.0.0.0:6379->6379/tcp

Images          18        2         25.51GB   10.94GB (42%)
Containers      3         2         24.58kB  4.096kB (16%)
Local Volumes   9         2         590.6MB  541.9MB (91%)
Build Cache     141       0         13.53GB  4.173GB (31%)

Docker Compose version v5.5.1
docker-compose: unavailable
~~~

The Docker daemon is reachable and the active context is rootless. PostgreSQL
and Valkey are healthy, with host ports published on 0.0.0.0; this is an
exposure concern for the deployment review.

## Listening ports

Command:

~~~sh
ss -H -lntp
ss -H -lnup
~~~

Result, with process IDs removed:

~~~text
TCP LISTEN
127.0.0.1:41378  MainThread
127.0.0.1:45135  MainThread
127.0.0.1:36731  MainThread
127.0.0.1:34041  MainThread
127.0.0.1:34743  MainThread
127.0.0.1:32853  MainThread
127.0.0.1:33037  MainThread
127.0.0.1:39955  MainThread
127.0.0.1:36889  MainThread
127.0.0.1:37438  MainThread
127.0.0.1:37549  MainThread
127.0.0.1:64663  MainThread
127.0.0.1:10843  MainThread
127.0.0.1:17671  MainThread
127.0.0.1:3001    node
127.0.0.1:8000    python3
127.0.0.1:5433    rootlesskit
0.0.0.0:22       process not shown
0.0.0.0:6379     rootlesskit
0.0.0.0:5432     rootlesskit
0.0.0.0:8765     python3
0.0.0.0:8766     python3
*:3459           node
*:4949           process not shown
[::]:22          process not shown

UDP UNCONN
127.0.0.54:53    system resolver
127.0.0.53:53    system resolver
~~~

The host-wide or wildcard listeners are:

| Port | Bind | Observed owner | Audit note |
|---:|---|---|---|
| 22 | 0.0.0.0, [::] | process not shown | Host administration surface |
| 5432 | 0.0.0.0 | rootlesskit | PostgreSQL container port |
| 6379 | 0.0.0.0 | rootlesskit | Valkey container port |
| 8765 | 0.0.0.0 | python3 | Service identity not established |
| 8766 | 0.0.0.0 | python3 | Service identity not established |
| 3459 | * | node | Service identity not established |
| 4949 | * | not shown | Requires ownership review |

Application/development listeners bound only to loopback were also present on
ports 3001, 8000, 5433, and the listed high ports. Loopback binding limits
direct network exposure from outside the host, but does not replace firewall
or reverse-proxy policy.

Finding: PostgreSQL and Valkey are published on all IPv4 interfaces, and ports
8765, 8766, 3459, and 4949 are also wildcard-bound. Agent 07/09 should verify
the intended firewall, authentication, and proxy policy before production use.

## Mounted filesystems

Command:

~~~sh
findmnt -rn -o TARGET,SOURCE,FSTYPE
~~~

Result:

~~~text
/sys sysfs sysfs
/proc proc proc
/dev udev devtmpfs
/dev/pts devpts devpts
/run tmpfs tmpfs
/sys/firmware/efi/efivars efivarfs efivarfs
/ /dev/mapper/ubuntu--vg--1-ubuntu--lv ext4
/sys/kernel/security securityfs securityfs
/dev/shm tmpfs tmpfs
/run/lock tmpfs tmpfs
/sys/fs/cgroup cgroup2 cgroup2
/sys/fs/pstore pstore pstore
/sys/fs/bpf bpf bpf
/proc/sys/fs/binfmt_misc systemd-1 autofs
/dev/hugepages hugetlbfs hugetlbfs
/dev/mqueue mqueue mqueue
/sys/kernel/debug debugfs debugfs
/sys/kernel/tracing tracefs tracefs
/sys/fs/fuse/connections fusectl fusectl
/sys/kernel/config configfs configfs
/usr/data /dev/mapper/data--vg-data--lv ext4
/boot /dev/sda2 ext4
/boot/efi /dev/sda1 vfat
/proc/sys/fs/binfmt_misc binfmt_misc binfmt_misc
~~~

Persistent application-relevant mounts are /, /usr/data, /boot, and /boot/efi.
The remaining entries are kernel, runtime, or device pseudo-filesystems. Docker
stores its root under /home/923873155/.local/share/docker, which resides on /
rather than /usr/data.

## Audit limitations and handoff

- This is a point-in-time host audit; it does not establish performance under
  application load, network reachability from another machine, firewall rules,
  TLS termination, or service ownership for every listener.
- Host GPU access is confirmed. Docker GPU passthrough is unverified because
  the NVIDIA container CLI and device nodes were unavailable to this shell and
  Docker reported no NVIDIA runtime.
- The next deployment review should resolve wildcard listener ownership,
  restrict database/cache exposure, verify container GPU requirements, and
  account for the nearly full swap and 79% root filesystem.

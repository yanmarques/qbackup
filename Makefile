user=bkpman

# install qubes-rpc backup carrier service
templatevm:
	@install -m 755 ./src/qubes.BackupCarrier /etc/qubes-rpc/

# install shell into backup user
server:
	@install -m 755 ./src/qbackup-shell /sbin/ && \
		usermod -s /sbin/qbackup-shell $(user)

# configure and enable ssh apparmor profile
server-aa:
	@install -m 644 ./apparmor.d/usr.sbin.qbackup-shell /etc/apparmor.d/ && \
		apparmor_parser -a /etc/apparmor.d/usr.sbin.qbackup-shell

lint/black:
	black --line-length 79 --diff --check qbackup/

lint/isort:
	isort --line-length 79 --diff --check-only qbackup/

lint/mypy:
	mypy --pretty qbackup/

lint: lint/black lint/isort lint/mypy

format/black:
	black --line-length 79 qbackup/

format/isort:
	isort --line-length 79 qbackup/

format: format/black format/isort

test:
	pytest
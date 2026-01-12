from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
	long_description = f.read()

setup(
	name="nextcloud_integration",
	version="0.0.1",
	description="Automatically create Nextcloud folders for new opportunities",
	author="ALKHORA",
	author_email="support@alkhora.com",
	packages=find_packages(where="nextcloud_integration", exclude=["tests", "tests.*"]),
	package_dir={"": "nextcloud_integration"},
	zip_safe=False,
	include_package_data=True,
	install_requires=[
		"requests>=2.28.0"
	]
)

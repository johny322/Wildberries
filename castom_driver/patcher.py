import io
import json
import logging
import os
import random
import re
import string
import sys
import zipfile
from distutils.version import LooseVersion
from urllib.request import urlopen, urlretrieve

logger = logging.getLogger(__name__)

IS_POSIX = sys.platform.startswith(("darwin", "cygwin", "linux"))


class Patcher(object):
    root_dir = os.path.dirname(__file__)

    url_repo = "https://chromedriver.storage.googleapis.com"
    zip_name = "chromedriver_%s.zip"
    exe_name = "chromedriver%s"

    platform = sys.platform
    if platform.endswith("win32"):
        zip_name %= "win32"
        exe_name %= ".exe"
    if platform.endswith("linux"):
        zip_name %= "linux64"
        exe_name %= ""
    if platform.endswith("darwin"):
        zip_name %= "mac64"
        exe_name %= ""

    # if platform.endswith("win32"):
    #     d = "~/appdata/roaming/undetected_chromedriver"
    # elif platform.startswith("linux"):
    #     d = "~/.local/share/undetected_chromedriver"
    # elif platform.endswith("darwin"):
    #     d = "~/Library/Application Support/undetected_chromedriver"
    # else:
    #     d = "~/.undetected_chromedriver"
    # data_path = os.path.abspath(os.path.expanduser(d))
    data_path = os.path.dirname(__file__)

    def __init__(self, executable_path=None, force=False, version_main: int = 0, download_version: bool = True):
        """
        Args:
            executable_path: None = automatic
                             a full file path to the chromedriver executable
            force: False
                    terminate processes which are holding lock
            version_main: 0 = auto
                specify main chrome version (rounded, ex: 82)
        """

        self.force = force
        self.executable_path = None

        if not executable_path:
            self.executable_path = os.path.join(self.data_path, self.exe_name)

        if not IS_POSIX:
            if executable_path:
                if not executable_path[-4:] == ".exe":
                    executable_path += ".exe"

        self.zip_path = os.path.join(self.data_path, self.zip_name)

        if not executable_path:
            self.executable_path = os.path.abspath(
                os.path.join(".", self.executable_path)
            )

        self._custom_exe_path = False

        if executable_path:
            self._custom_exe_path = True
            self.executable_path = executable_path
        self.version_main = version_main
        self.version_full = None

    def auto(self, executable_path=None, force=False, version_main=None, download_version=True):
        """"""
        if executable_path:
            if os.path.exists(executable_path):
                self.executable_path = executable_path
                self._custom_exe_path = True

        if self._custom_exe_path:
            ispatched = self.is_binary_patched(self.executable_path)
            if not ispatched:
                return self.patch_exe()
            else:
                return

        if force is True:
            self.force = force

        try:
            os.unlink(self.executable_path)
        except PermissionError:
            if self.force:
                self.force_kill_instances(self.executable_path)
                return self.auto(force=not self.force)
            try:
                if self.is_binary_patched():
                    # assumes already running AND patched
                    return True
            except PermissionError:
                pass
            # return False
        except FileNotFoundError:
            pass

        if version_main:
            self.version_main = version_main
            release = self.fetch_release_number()
            # self.version_main = release.version[0]
            self.version_full = release
            # self.unzip_package(self.fetch_package())
        else:
            chrome_version = self.get_chrome_version()
            print(f'Chrome version: {chrome_version}')
            if chrome_version:
                release = chrome_version
                # self.version_main = release.version[0]
                self.version_full = self.fetch_release_number()
            else:
                release = self.fetch_release_number()
                # self.version_main = release.version[0]
                self.version_full = release
        self.version_main = release.version[0]
        self.unzip_package(self.fetch_package())

        return self.patch()

    def patch(self):
        self.patch_exe()
        return self.is_binary_patched()

    def fetch_release_number(self):
        """
        Gets the latest major version available, or the latest major version of self.target_version if set explicitly.
        :return: version string
        :rtype: LooseVersion
        """
        path = "/latest_release"
        if self.version_main:
            path += f"_{self.version_main}"
        path = path.upper()
        logger.debug("getting release number from %s" % path)
        return LooseVersion(urlopen(self.url_repo + path).read().decode())

    def parse_exe_version(self):
        with io.open(self.executable_path, "rb") as f:
            for line in iter(lambda: f.readline(), b""):
                match = re.search(br"platform_handle\x00content\x00([0-9.]*)", line)
                if match:
                    return LooseVersion(match[1].decode())

    def fetch_package(self):
        """
        Downloads ChromeDriver from source
        :return: path to downloaded file
        """
        u = "%s/%s/%s" % (self.url_repo, self.version_full.vstring, self.zip_name)
        logger.debug("downloading from %s" % u)
        print('Скачивание драйвера с: ', u)
        dwl_path = os.path.join(self.data_path, self.zip_name)
        # dwl_path = self.zip_name
        print('Путь до zip файла: ', dwl_path)
        return urlretrieve(u, dwl_path)[0]

    def unzip_package(self, fp):
        """
        Does what it says
        :return: path to unpacked executable
        """
        logger.debug("unzipping %s" % fp)
        # try:
        #     os.unlink(self.zip_path)
        # except (FileNotFoundError, OSError):
        #     pass

        # os.makedirs(self.data_path, mode=0o755, exist_ok=True)

        with zipfile.ZipFile(fp, mode="r") as zf:
            zf.extract(self.exe_name, os.path.dirname(self.executable_path))
        os.remove(fp)
        os.chmod(self.executable_path, 0o755)
        return self.executable_path

    @staticmethod
    def force_kill_instances(exe_name):
        """
        kills running instances.
        :param: executable name to kill, may be a path as well
        :return: True on success else False
        """
        exe_name = os.path.basename(exe_name)
        if IS_POSIX:
            r = os.system("kill -f -9 $(pidof %s)" % exe_name)
        else:
            r = os.system("taskkill /f /im %s" % exe_name)
        return not r

    @staticmethod
    def gen_random_cdc():
        cdc = random.choices(string.ascii_lowercase, k=26)
        cdc[-6:-4] = map(str.upper, cdc[-6:-4])
        cdc[2] = cdc[0]
        cdc[3] = "_"
        return "".join(cdc).encode()

    def is_binary_patched(self, executable_path=None):
        """simple check if executable is patched.
        :return: False if not patched, else True
        """
        executable_path = executable_path or self.executable_path
        with io.open(executable_path, "rb") as fh:
            for line in iter(lambda: fh.readline(), b""):
                if b"cdc_" in line:
                    return False
            else:
                return True

    def patch_exe(self):
        """
        Patches the ChromeDriver binary
        :return: False on failure, binary name on success
        """
        logger.info("patching driver executable %s" % self.executable_path)

        linect = 0
        replacement = self.gen_random_cdc()
        with io.open(self.executable_path, "r+b") as fh:
            for line in iter(lambda: fh.readline(), b""):
                if b"cdc_" in line:
                    fh.seek(-len(line), 1)
                    newline = re.sub(b"cdc_.{22}", replacement, line)
                    fh.write(newline)
                    linect += 1
            return linect

    @staticmethod
    def find_chrome_executable():
        """
        Finds the chrome, chrome beta, chrome canary, chromium executable
        Returns
        -------
        executable_path :  str
            the full file path to found executable
        """
        candidates = set()
        if IS_POSIX:
            for item in os.environ.get("PATH").split(os.pathsep):
                for subitem in ("google-chrome", "chromium", "chromium-browser"):
                    candidates.add(os.sep.join((item, subitem)))
            if "darwin" in sys.platform:
                candidates.update(
                    ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
                )
        else:
            for item in map(
                    os.environ.get, ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")
            ):
                for subitem in (
                        "Google/Chrome/Application",
                        "Google/Chrome Beta/Application",
                        "Google/Chrome Canary/Application",
                ):
                    candidates.add(os.sep.join((item, subitem, "chrome.exe")))
        for candidate in candidates:
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                return os.path.normpath(candidate)

    def get_chrome_version(self):
        """

        :return:
        """
        chrome_path = self.find_chrome_executable()
        if chrome_path:
            chrome_dir = os.path.dirname(chrome_path)
            chrome_files = os.listdir(chrome_dir)
            for file in chrome_files:
                math = re.fullmatch('\d{2,3}\.0\.\d{4}\.\d{1,}', file)
                if math:
                    chrome_version = math.string
                    return LooseVersion(chrome_version)
        else:
            return

    def conf_file(self):
        conf_path = os.path.join(self.data_path, 'conf.json')
        if not os.path.exists(conf_path):
            with open(conf_path, 'w', encoding='utf-8') as file:
                conf = {
                    "chrome version": "",
                    "chromedriver version": ""
                }
                json.dump(conf, file, indent=4)

    def __repr__(self):
        return "{0:s}({1:s})".format(
            self.__class__.__name__,
            self.executable_path,
        )


if __name__ == '__main__':
    p = Patcher()
    print(p.auto())

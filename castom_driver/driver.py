import random
import sys
from time import sleep

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.remote.webelement import WebElement

from selenium_stealth import stealth

from castom_driver.patcher import Patcher


def timeout(value=None):
    if value is None:
        sleep(random.uniform(1.5, 2.5))
    elif value == 0:
        sleep(random.uniform(0, 0.4))
    elif len(value) > 1:
        sleep(random.uniform(value[0], value[1]))
    else:
        sleep(value)


def ac_timeout(value=0):
    if value is None:
        return random.uniform(1.5, 2.5)
    elif value == 0:
        return random.uniform(0, 0.4)
    else:
        return value


class Driver(webdriver.Chrome):
    def __init__(self,
                 # Chromedriver parameters
                 executable_path=None,
                 port=0,
                 options=webdriver.ChromeOptions(),
                 service_args=None,
                 desired_capabilities=None,
                 service_log_path=None,
                 chrome_options=None,
                 keep_alive=True,

                 force=False,
                 version_main=None,
                 stealth_driver=True
                 ):

        options.add_experimental_option("excludeSwitches",
                                        ["ignore-certificate-errors", "safebrowsing-disable-download-protection",
                                         "safebrowsing-disable-auto-update", "disable-client-side-phishing-detection",
                                         "enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features=AutomationControlled")

        # options.add_argument('--window-size=600,600')
        # options.add_argument('--headless')

        self.patcher = Patcher(executable_path, force, version_main)
        self.patcher.auto(executable_path, force, version_main)

        if not executable_path:
            executable_path = self.patcher.executable_path

        super().__init__(executable_path=executable_path,
                         port=port,
                         options=options,
                         service_args=service_args,
                         desired_capabilities=desired_capabilities,
                         service_log_path=service_log_path,
                         chrome_options=chrome_options,
                         keep_alive=keep_alive)
        self.stealth_driver = stealth_driver
        if self.stealth_driver:
            stealth(self,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform=sys.platform.title(),  # Win32
                    # platform='Win32',
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                    run_on_insecure_origins=True
                    )

    def get_in_new_tab(self, url):
        if self.stealth_driver:
            self.execute_script("window.open('chrome://new-tab-page/','_blank');")
            self.switch_to.window(self.window_handles[-1])
            stealth(self,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform=sys.platform.title(),  # Win32
                    # platform='Win32',
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                    run_on_insecure_origins=True
                    )
            self.get(url)
        else:
            self.execute_script(f"window.open('{url}','_blank');")

    def change_user_agent(self, user_agent):
        self.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})

    def get_start_page(self):
        self.get('chrome://new-tab-page/')

    def download_source(self, file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(self.page_source)

    def download_html(self, file_path: str):
        sp = file_path.split('.')
        if len(sp) == 1:
            file_path += '.html'
        elif sp[-1] != 'html':
            file_path = ''.join(sp[:-1]) + '.html'
        if not file_path.endswith('.html'):
            file_path += '.html'
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(self.page_source)

    @staticmethod
    def person_send_keys(webelement: WebElement, value):
        timeout(0)
        for v in value:
            webelement.send_keys(v)
            timeout(0)

    def person_click(self, webelement: WebElement):
        ActionChains(self).move_to_element(webelement).pause(ac_timeout()).click().pause(ac_timeout()).perform()

    def scroll_to(self, webelement: WebElement, y_corr=0):
        half_height = self.get_window_size()['height'] / 2
        if webelement == 'half':
            while y_corr < half_height:
                self.execute_script(f"window.scrollTo(0, {y_corr})")
                y_corr += 1
        else:
            loc = webelement.location
            while y_corr < loc['y'] - half_height:
                self.execute_script(f"window.scrollTo(0, {y_corr})")
                y_corr += 1

    def scroll_until_presence(self, locator, y_corr=0) -> WebElement:
        while True:
            try:
                webelement = self.find_element(locator[0], locator[1])
                return webelement
            except NoSuchElementException:
                self.execute_script(f"window.scrollTo(0, {y_corr})")
                y_corr += 2
                if y_corr >= 100000:
                    break

    def execute_undetected_script(self):
        self.execute_cdp_cmd(
            'Page.addScriptToEvaluateOnNewDocument', {
                "source": '''
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            });
                            Object.defineProperty(navigator, 'plugins', {
                                    get: function() { return {"0":{"0":{}},"1":{"0":{}},"2":{"0":{},"1":{}}}; }
                            });
                            window.chrome =
                            {
                              app: {
                                isInstalled: false,
                              },
                              webstore: {
                                onInstallStageChanged: {},
                                onDownloadProgress: {},
                              },
                              runtime: {
                                PlatformOs: {
                                  MAC: 'mac',
                                  WIN: 'win',
                                  ANDROID: 'android',
                                  CROS: 'cros',
                                  LINUX: 'linux',
                                  OPENBSD: 'openbsd',
                                },
                                PlatformArch: {
                                  ARM: 'arm',
                                  X86_32: 'x86-32',
                                  X86_64: 'x86-64',
                                },
                                PlatformNaclArch: {
                                  ARM: 'arm',
                                  X86_32: 'x86-32',
                                  X86_64: 'x86-64',
                                },
                                RequestUpdateCheckStatus: {
                                  THROTTLED: 'throttled',
                                  NO_UPDATE: 'no_update',
                                  UPDATE_AVAILABLE: 'update_available',
                                },
                                OnInstalledReason: {
                                  INSTALL: 'install',
                                  UPDATE: 'update',
                                  CHROME_UPDATE: 'chrome_update',
                                  SHARED_MODULE_UPDATE: 'shared_module_update',
                                },
                                OnRestartRequiredReason: {
                                  APP_UPDATE: 'app_update',
                                  OS_UPDATE: 'os_update',
                                  PERIODIC: 'periodic',
                                },
                              },
                            };
                            '''
            }
        )

    def execute_full_undetected_script(self):
        self.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            "source": '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                    get: function() { return {"0":{"0":{}},"1":{"0":{}},"2":{"0":{},"1":{}}}; }
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ["en-US", "en"]
            });
            Object.defineProperty(navigator, 'mimeTypes', {
                get: function() { return {"0":{},"1":{},"2":{},"3":{}}; }
            });

            window.screenY=23;
            window.screenTop=23;
            window.outerWidth=1337;
            window.outerHeight=825;
            window.chrome =
            {
              app: {
                isInstalled: false,
              },
              webstore: {
                onInstallStageChanged: {},
                onDownloadProgress: {},
              },
              runtime: {
                PlatformOs: {
                  MAC: 'mac',
                  WIN: 'win',
                  ANDROID: 'android',
                  CROS: 'cros',
                  LINUX: 'linux',
                  OPENBSD: 'openbsd',
                },
                PlatformArch: {
                  ARM: 'arm',
                  X86_32: 'x86-32',
                  X86_64: 'x86-64',
                },
                PlatformNaclArch: {
                  ARM: 'arm',
                  X86_32: 'x86-32',
                  X86_64: 'x86-64',
                },
                RequestUpdateCheckStatus: {
                  THROTTLED: 'throttled',
                  NO_UPDATE: 'no_update',
                  UPDATE_AVAILABLE: 'update_available',
                },
                OnInstalledReason: {
                  INSTALL: 'install',
                  UPDATE: 'update',
                  CHROME_UPDATE: 'chrome_update',
                  SHARED_MODULE_UPDATE: 'shared_module_update',
                },
                OnRestartRequiredReason: {
                  APP_UPDATE: 'app_update',
                  OS_UPDATE: 'os_update',
                  PERIODIC: 'periodic',
                },
              },
            };
            window.navigator.chrome =
            {
              app: {
                isInstalled: false,
              },
              webstore: {
                onInstallStageChanged: {},
                onDownloadProgress: {},
              },
              runtime: {
                PlatformOs: {
                  MAC: 'mac',
                  WIN: 'win',
                  ANDROID: 'android',
                  CROS: 'cros',
                  LINUX: 'linux',
                  OPENBSD: 'openbsd',
                },
                PlatformArch: {
                  ARM: 'arm',
                  X86_32: 'x86-32',
                  X86_64: 'x86-64',
                },
                PlatformNaclArch: {
                  ARM: 'arm',
                  X86_32: 'x86-32',
                  X86_64: 'x86-64',
                },
                RequestUpdateCheckStatus: {
                  THROTTLED: 'throttled',
                  NO_UPDATE: 'no_update',
                  UPDATE_AVAILABLE: 'update_available',
                },
                OnInstalledReason: {
                  INSTALL: 'install',
                  UPDATE: 'update',
                  CHROME_UPDATE: 'chrome_update',
                  SHARED_MODULE_UPDATE: 'shared_module_update',
                },
                OnRestartRequiredReason: {
                  APP_UPDATE: 'app_update',
                  OS_UPDATE: 'os_update',
                  PERIODIC: 'periodic',
                },
              },
            };
            ['height', 'width'].forEach(property => {
                const imageDescriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, property);

                // redefine the property with a patched descriptor
                Object.defineProperty(HTMLImageElement.prototype, property, {
                    ...imageDescriptor,
                    get: function() {
                        // return an arbitrary non-zero dimension if the image failed to load
            if (this.complete && this.naturalHeight == 0) {
                        return 20;
                    }
                        return imageDescriptor.get.apply(this);
                    },
                });
            });

            const getParameter = WebGLRenderingContext.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Open Source Technology Center';
                }
                if (parameter === 37446) {
                    return 'Mesa DRI Intel(R) Ivybridge Mobile ';
                }

                return getParameter(parameter);
            };

            const elementDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');

            Object.defineProperty(HTMLDivElement.prototype, 'offsetHeight', {
                ...elementDescriptor,
                get: function() {
                    if (this.id === 'modernizr') {
                    return 1;
                    }
                    return elementDescriptor.get.apply(this);
                },
            });
            '''
        })

    def force_kill_instances(self):
        print(self.patcher.force_kill_instances(self.patcher.exe_name))


if __name__ == '__main__':
    options = webdriver.ChromeOptions()
    d = Driver(executable_path='chromedriver.exe', stealth_driver=False, options=options)
    try:
        d.get('https://google.com/')
        timeout()
    finally:
        d.close()
        d.quit()

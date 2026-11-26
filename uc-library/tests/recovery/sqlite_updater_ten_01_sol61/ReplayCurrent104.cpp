#include "core/portable/corefile.h"
#include "presonus/surface_update/FirmwareUpdateComponent.hpp"
#include <cassert>
#include <csignal>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <curl/curl.h>
#include <dlfcn.h>
#include <execinfo.h>
#include <iostream>
#include <map>
#include <pthread.h>
#include <sstream>
#include <string>
#include <sys/socket.h>
#include <time.h>
#include <vector>
using U = Presonus::UUX::FirmwareUpdater;
using P = presonus::uux::PathView;
namespace presonus::surface_update {
struct ConstructionAccess {
  static void setup(Presonus::Surface::FirmwareUpdateComponent &c) {
    c.product = 25;
    c.serial = 42;
  }
  static void *worker(Presonus::Surface::FirmwareUpdateComponent &c) {
    return c.worker.get();
  }
};
} // namespace presonus::surface_update
namespace {
void *library;
std::map<std::string, std::string> cfg;
std::vector<std::string> calls;
std::string quote(const std::string &s) {
  std::string r = "\"";
  for (unsigned char c : s) {
    if (c == '"' || c == '\\') {
      r += '\\';
      r += c;
    } else if (c == '\n')
      r += "\\n";
    else if (c == '\r')
      r += "\\r";
    else if (c == '\t')
      r += "\\t";
    else
      r += c;
  }
  return r + '"';
}
std::string q(const char *s) { return quote(s ? s : ""); }
void call(std::initializer_list<std::string> parts) {
  std::string s = "[";
  for (auto &p : parts) {
    if (s.size() > 1)
      s += ",";
    s += p;
  }
  calls.push_back(s + "]");
}
int val(const char *key, int fallback = 0) {
  auto i = cfg.find(key);
  return i == cfg.end() ? fallback : static_cast<int>(std::stoll(i->second));
}
bool flag(const char *key, bool fallback = true) {
  return val(key, fallback) != 0;
}
const char *uri() {
  auto i = cfg.find("uri");
  return i == cfg.end() ? "https://example.invalid/fw.bin" : i->second.c_str();
}
template <class T> T original(const char *name) {
  auto p = dlsym(library, name);
  if (!p) {
    std::cerr << dlerror();
    std::abort();
  }
  return reinterpret_cast<T>(p);
}
void fill(U &u, const char *version) {
  P::requestField(u, 2) = "rm32";
  P::requestField(u, 3) = "RM3E42";
  P::requestField(u, 4) = "aa:bb:cc:dd:ee:ff";
  P::requestField(u, 5) = version;
  P::requestField(u, 6) = "0123456789abcdef0123456789abcdef";
  P::requestField(u, 7) = "1234";
}
struct Listener : Presonus::UUX::FirmwareUpdateListener {
  void doAlert(const char *a, const char *b, const char *c) override {
    call({q("alert"), q(a), q(b), q(c)});
  }
  void dismissAlert() override { call({q("dismiss")}); }
  void onProgress(const char *a, const char *b, float) override {
    call({q("progress"), q(a), q(b)});
  }
};
Core::Portable::BackgroundTask *queued = nullptr;
Core::Portable::Parameter *parameter = nullptr;
bool lifecycle = false, taskRun = false, allocations = false;
std::size_t allocationSize = 0;
void *allocationPointer = nullptr;
void *workerPointer = nullptr;
void *objectPointer = nullptr;
Core::Portable::ParamInfo parameterInfo =
    PARAM_FLOAT(0, "fixture", -100, 100, 0, 1, nullptr, 0, 0, 0);
struct CaptureParam : Core::Portable::NumericParam {
  CaptureParam() : NumericParam(parameterInfo) {}
  float getValue() const override {
    auto i = cfg.find("value");
    return i == cfg.end() ? 0.f : std::stof(i->second);
  }
  void setValue(float v, bool edit) override {
    std::ostringstream out;
    out << v;
    call({q("set"), out.str(), edit ? "true" : "false"});
  }
  void enable(bool state) override {
    call({q("enable"), state ? "true" : "false"});
  }
};
bool captureUpdate = false;
bool active = false;
bool helperActive = false;
FILE *responseFile = nullptr;
curl_write_callback responseCallback = nullptr;
bool tracking = false;
void *tracked = nullptr;
} // namespace
// Application boundaries are interposed for isolated target observations. Main
// enters the actual production body through its shared-library symbol address.
extern "C" int capturePrepare(U *) asm(
    "_ZN8Presonus3UUX15FirmwareUpdater28prepareFirmwareRequestFieldsEv");
extern "C" int capturePrepare(U *) {
  call({q("prepare")});
  return val("prepare");
}
extern "C" int captureLocal(U *) asm(
    "_ZN8Presonus3UUX15FirmwareUpdater21doLocalFirmwareUpdateEv");
extern "C" int captureLocal(U *) {
  call({q("local")});
  return val("local", 2);
}
extern "C" int
captureUsb(U *) asm("_ZN8Presonus3UUX15FirmwareUpdater19doUsbFirmwareUpdateEv");
extern "C" int captureUsb(U *) {
  call({q("usb")});
  return val("usb", 2);
}
extern "C" int captureNetwork(U *) asm(
    "_ZN8Presonus3UUX15FirmwareUpdater23doNetworkFirmwareUpdateEv");
extern "C" int captureNetwork(U *) {
  call({q("network")});
  return val("network");
}
extern "C" int captureExecute(U *, const char *) asm(
    "_ZN8Presonus3UUX15FirmwareUpdater24executeBashUpgradeScriptEPKc");
extern "C" int captureExecute(U *, const char *s) {
  call({q("execute"), q(s)});
  return 123;
}
extern "C" int
captureSpin(U *,
            int) asm("_ZN8Presonus3UUX15FirmwareUpdater18spinUpgradeDisplayEi");
extern "C" int captureSpin(U *, int p) {
  call({q("spin"), std::to_string(p)});
  return val("script");
}
extern "C" int captureUpdateBody(U *) asm(
    "_ZN8Presonus3UUX15FirmwareUpdater14updateFirmwareEv");
extern "C" int captureUpdateBody(U *u) {
  call({q("update"), q(P::requestField(*u, 0).str()),
        P::animated(*u) ? "true" : "false"});
  return 0;
}
extern "C" void
captureAdd(Core::Portable::BackgroundWorker *,
           Core::Portable::BackgroundTask
               *) asm("__wrap__ZN4Core8Portable16BackgroundWorker7addTaskEPNS0_"
                      "14BackgroundTaskE");
extern "C" void captureAdd(Core::Portable::BackgroundWorker *,
                           Core::Portable::BackgroundTask *t) {
  assert(!queued);
  queued = t;
  if (allocations) {
    assert(allocationPointer == t);
    allocations = false;
    call({q("host-new"), std::to_string(allocationSize)});
    allocations = true;
  }
  call({q("add-task"), "25", "42"});
}
extern "C" Core::Portable::Parameter *
captureGet(const Core::Portable::Component *,
           int) asm("__wrap__ZNK4Core8Portable9Component17getParameterByTagEi");
extern "C" Core::Portable::Parameter *
captureGet(const Core::Portable::Component *, int tag) {
  call({q("get-param"), std::to_string(tag)});
  return tag == 0 && !flag("trigger") ? nullptr : parameter;
}
extern "C" void
captureBase(Core::Portable::Component *, Core::Portable::Parameter *, int) asm(
    "__wrap__ZN4Core8Portable9Component12paramChangedEPNS0_9ParameterEi");
extern "C" void captureBase(Core::Portable::Component *,
                            Core::Portable::Parameter *, int) {
  call({q("base-changed")});
}
extern "C" void
captureDoUpdate(Presonus::Surface::FirmwareUpdateComponent *) asm(
    "_ZN8Presonus7Surface23FirmwareUpdateComponent8doUpdateEv");
extern "C" void captureDoUpdate(Presonus::Surface::FirmwareUpdateComponent *) {
  call({q("do-update")});
}
extern "C" void realTerminate(Core::Portable::BackgroundWorker *) asm(
    "__real__ZN4Core8Portable16BackgroundWorker9terminateEv");
extern "C" void captureTerminate(Core::Portable::BackgroundWorker *) asm(
    "__wrap__ZN4Core8Portable16BackgroundWorker9terminateEv");
extern "C" void captureTerminate(Core::Portable::BackgroundWorker *w) {
  if (lifecycle)
    call({q("terminate")});
  realTerminate(w);
}
extern "C" void realComponentDtor(Core::Portable::Component *) asm(
    "__real__ZN4Core8Portable9ComponentD2Ev");
extern "C" void captureComponentDtor(Core::Portable::Component *) asm(
    "__wrap__ZN4Core8Portable9ComponentD2Ev");
extern "C" void captureComponentDtor(Core::Portable::Component *c) {
  if (lifecycle)
    call({q("component-dtor")});
  realComponentDtor(c);
}
extern "C" void *realNew(std::size_t) asm("__real__Znwm");
extern "C" void *captureNew(std::size_t) asm("__wrap__Znwm");
extern "C" void *captureNew(std::size_t n) {
  void *p = realNew(n);
  if (allocations) {
    allocationSize = n;
    allocationPointer = p;
  }
  return p;
}
extern "C" void realDelete(void *) asm("__real__ZdlPv");
extern "C" void realSizedDelete(void *, std::size_t) asm("__real__ZdlPvm");
void recordDelete(void *p) {
  if (lifecycle && p == workerPointer)
    call({q("worker-delete")});
  else if (lifecycle && p == objectPointer)
    call({q("delete-object")});
}
extern "C" void captureDelete(void *) asm("__wrap__ZdlPv");
extern "C" void captureDelete(void *p) {
  recordDelete(p);
  realDelete(p);
}
extern "C" void captureSizedDelete(void *, std::size_t) asm("__wrap__ZdlPvm");
extern "C" void captureSizedDelete(void *p, std::size_t n) {
  recordDelete(p);
  realSizedDelete(p, n);
}
extern "C" void
captureCtor(U *, int, int, Presonus::UUX::FirmwareUpdateListener *) asm(
    "_ZN8Presonus3UUX15FirmwareUpdaterC1EiiPNS0_22FirmwareUpdateListenerE");
extern "C" void captureCtor(U *u, int p, int s,
                            Presonus::UUX::FirmwareUpdateListener *l) {
  if (taskRun)
    call({q("updater-ctor"), std::to_string(p), std::to_string(s)});
  original<void (*)(U *, int, int, Presonus::UUX::FirmwareUpdateListener *)>(
      "_ZN8Presonus3UUX15FirmwareUpdaterC1EiiPNS0_22FirmwareUpdateListenerE")(
      u, p, s, l);
}
extern "C" void captureDtor(U *) asm("_ZN8Presonus3UUX15FirmwareUpdaterD1Ev");
extern "C" void captureDtor(U *u) {
  if (taskRun)
    call({q("updater-dtor")});
  original<void (*)(U *)>("_ZN8Presonus3UUX15FirmwareUpdaterD1Ev")(u);
}
extern "C" double captureSeconds() asm("_ZN4Core11SystemClock10getSecondsEv");
extern "C" double captureSeconds() { return 1234.; }
// O3 inlines getSeconds: capture its actual POSIX boundary only during the
// synchronous request-field observation. Keep CCL conversion and real errors.
static bool captureRequestClock = false;
extern "C" int __real_clock_gettime(clockid_t, struct timespec *);
extern "C" int __wrap_clock_gettime(clockid_t id, struct timespec *value) {
  const int result = __real_clock_gettime(id, value);
  if (result == 0 && captureRequestClock && id == CLOCK_MONOTONIC) {
    value->tv_sec = 1234;
    value->tv_nsec = 0;
  }
  return result;
}
extern "C" void
captureSleep(unsigned) asm("__wrap__ZN4Core8Platform13CurrentThread5sleepEj");
extern "C" void captureSleep(unsigned n) {
  call({q("sleep"), std::to_string(n)});
}
extern "C" char **environ;
extern "C" char *getenv(const char *name) noexcept {
  if (active && std::strcmp(name, "HOME") == 0) {
    auto i = cfg.find("temp");
    return const_cast<char *>(i == cfg.end() ? "/offline/" : i->second.c_str());
  }
  const auto n = std::strlen(name);
  for (char **p = environ; p && *p; ++p)
    if (std::strncmp(*p, name, n) == 0 && (*p)[n] == '=')
      return *p + n + 1;
  return nullptr;
}
extern "C" int system(const char *s) {
  call({q("system"), q(s)});
  return 0;
}
extern "C" int remove(const char *s) {
  call({q("delete"), q(s)});
  return 0;
}
extern "C" FILE *fopen(const char *path, const char *mode) {
  if (!active)
    return nullptr;
  call({q(mode[0] == 'w' ? "create" : "open"), q(path)});
  static char mac[128], hash[128], response[2048], other[4096];
  char *buffer = other;
  std::size_t size = sizeof(other);
  if (std::string(path) == "/sfs/hwaddr.txt") {
    if (!flag("mac_open"))
      return nullptr;
    std::strcpy(mac, "aa:bb:cc:dd:ee:ff ");
    buffer = mac;
    size = sizeof(mac);
  } else if (std::string(path) == "md5scratch") {
    if (!flag("hash_open"))
      return nullptr;
    std::strcpy(hash, "0123456789abcdef0123456789abcdef ");
    buffer = hash;
    size = sizeof(hash);
  } else if (helperActive || std::string(path) == "/offline/response") {
    if (helperActive && !flag("create"))
      return nullptr;
    if (!flag("archive"))
      return nullptr;
    std::snprintf(response, sizeof(response),
                  "{\"result_code\":%d,\"firmware_URI\":%s}", val("code"),
                  quote(uri()).c_str());
    buffer = response;
    size = sizeof(response);
  } else {
    std::cerr << "forbidden file " << path;
    std::abort();
  }
  FILE *file = fmemopen(buffer, size, mode);
  if (helperActive)
    responseFile = file;
  return file;
}
extern "C" std::size_t fwrite(const void *data, std::size_t size,
                              std::size_t count, FILE *file) {
  auto real =
      reinterpret_cast<std::size_t (*)(const void *, std::size_t, std::size_t,
                                       FILE *)>(dlsym(RTLD_NEXT, "fwrite"));
  if (helperActive && file == responseFile) {
    std::size_t bytes = size * count;
    call({q("write"),
          quote(std::string(static_cast<const char *>(data), bytes))});
    return val("write_result", static_cast<int>(count));
  }
  return real(data, size, count, file);
}
extern "C" int fclose(FILE *file) {
  if (helperActive && file == responseFile) {
    call({q("close")});
    responseFile = nullptr;
  }
  auto real = reinterpret_cast<int (*)(FILE *)>(dlsym(RTLD_NEXT, "fclose"));
  return real(file);
}
extern "C" void realFileCtor(void *, FILE *) asm(
    "__real__ZN4Core8Platform15PosixFileStreamC1EP8_IO_FILE");
extern "C" void captureFileCtor(void *, FILE *) asm(
    "__wrap__ZN4Core8Platform15PosixFileStreamC1EP8_IO_FILE");
extern "C" void captureFileCtor(void *p, FILE *f) {
  if (helperActive)
    call({q("stream-ctor")});
  realFileCtor(p, f);
}
extern "C" void
realFileDtor(void *) asm("__real__ZN4Core8Platform15PosixFileStreamD1Ev");
extern "C" void
captureFileDtor(void *) asm("__wrap__ZN4Core8Platform15PosixFileStreamD1Ev");
extern "C" void captureFileDtor(void *p) {
  if (helperActive)
    call({q("stream-dtor")});
  realFileDtor(p);
}
extern "C" int socket(int, int, int) noexcept { std::abort(); }
extern "C" int connect(int, const struct sockaddr *, socklen_t) {
  std::abort();
}
extern "C" int pthread_create(pthread_t *, const pthread_attr_t *,
                              void *(*)(void *), void *) noexcept {
  std::abort();
}
extern "C" int fork() { std::abort(); }
extern "C" int execve(const char *, char *const[], char *const[]) {
  std::abort();
}
extern "C" CURLcode curl_global_init(long) {
  call({q("global-init")});
  return static_cast<CURLcode>(val("global"));
}
extern "C" void curl_global_cleanup() { call({q("global-cleanup")}); }
extern "C" CURL *curl_easy_init() {
  call({q("easy-init")});
  return flag("easy_fail", false) ? nullptr : reinterpret_cast<CURL *>(0x1234);
}
extern "C" CURLcode curl_easy_setopt(CURL *, CURLoption opt, ...) {
  va_list ap;
  va_start(ap, opt);
  if (opt == CURLOPT_URL || opt == CURLOPT_POSTFIELDS) {
    const char *s = va_arg(ap, const char *);
    call({q("option"), std::to_string(opt), q(s)});
  } else if (opt == CURLOPT_WRITEFUNCTION) {
    responseCallback = va_arg(ap, curl_write_callback);
    call({q("option"), std::to_string(opt), q("callback")});
  } else {
    long n = va_arg(ap, long);
    call({q("option"), std::to_string(opt), std::to_string(n)});
  }
  va_end(ap);
  return CURLE_OK;
}
extern "C" CURLcode curl_easy_perform(CURL *) {
  call({q("perform")});
  return static_cast<CURLcode>(val("curl_result"));
}
extern "C" void curl_easy_cleanup(CURL *) { call({q("easy-cleanup")}); }
// Provider temp-path adaptation uses a real FileName and the real pinned API.
extern "C" void captureTemp(Core::Portable::FileName &p, int) asm(
    "__wrap__ZN4Core8Platform15PosixFileSystem12getDirectoryERNS_"
    "8Portable8FileNameENS0_11IFileSystem7DirTypeE");
extern "C" void captureTemp(Core::Portable::FileName &p, int) {
  p = "/offline/";
}
int main(int argc, char **argv) {
  std::signal(SIGSEGV, [](int) {
    void *trace[32];
    int n = backtrace(trace, 32);
    backtrace_symbols_fd(trace, n, 2);
    std::_Exit(139);
  });
  assert(argc >= 4);
  library = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
  if (!library) {
    std::cerr << dlerror();
    return 2;
  }
  active = true;
  const std::string symbol = argv[2];
  const char *version = argv[3];
  for (int i = 4; i < argc; ++i) {
    std::string s = argv[i];
    auto p = s.find('=');
    cfg[s.substr(0, p)] = s.substr(p + 1);
  }
  Listener l;
  U u(val("product", 23), 42, flag("listener") ? &l : nullptr);
  fill(u, version);
  P::firmwareVersion(u, version);
  calls.clear();
  calls.reserve(1024);
  std::string fields;
  if (symbol.find("FirmwareUpdaterC") != std::string::npos) {
    alignas(U) unsigned char storage[sizeof(U)];
    auto &real = *reinterpret_cast<U *>(storage);
    original<void (*)(U *, int, int, Presonus::UUX::FirmwareUpdateListener *)>(
        symbol.c_str())(&real, val("product", 23), 42, &l);
    fields = ",\"product\":" + q(P::requestField(real, 2).str()) +
             ",\"serial\":" + q(P::requestField(real, 3).str()) +
             ",\"completion\":" + q(P::requestField(real, 1).str()) +
             ",\"usb\":" + q(P::usb(real).str()) +
             ",\"url\":" + q(P::url(real).str());
    original<void (*)(U *)>("_ZN8Presonus3UUX15FirmwareUpdaterD1Ev")(&real);
  } else if (symbol.find("prepareFirmware") != std::string::npos) {
    captureRequestClock = true;
    int n = original<int (*)(U *)>(symbol.c_str())(&u);
    captureRequestClock = false;
    fields = ",\"mac\":" + q(P::requestField(u, 4).str()) +
             ",\"firmware\":" + q(P::requestField(u, 5).str()) +
             ",\"key\":" + q(P::requestField(u, 6).str()) +
             ",\"timestamp\":" + q(P::requestField(u, 7).str()) +
             ",\"result\":" + std::to_string(static_cast<unsigned>(n));
  } else if (symbol.find("doNetworkFirmware") != std::string::npos ||
             symbol.find("FirmwareUpdater14update") != std::string::npos) {
    int n = original<int (*)(U *)>(symbol.c_str())(&u);
    fields = ",\"result\":" + std::to_string(n);
  } else if (symbol == "_ZL19curlRequestCallbackPvjjS_") {
    auto savedTemp = cfg.find("temp");
    std::string tempValue = savedTemp == cfg.end() ? "" : savedTemp->second;
    cfg.erase("temp");
    original<int (*)(U *)>(
        "_ZN8Presonus3UUX15FirmwareUpdater23doNetworkFirmwareUpdateEv")(&u);
    if (!tempValue.empty())
      cfg["temp"] = tempValue;
    assert(responseCallback);
    calls.clear();
    helperActive = true;
    char data[] = "abcdef";
    std::size_t n = 0;
    for (int i = 0; i < val("repeat", 1); ++i)
      n = responseCallback(data,
                           flag("bridge_wide", false)
                               ? (std::size_t(1) << 32)
                               : static_cast<unsigned>(val("size", 2)),
                           static_cast<unsigned>(val("count", 3)), nullptr);
    helperActive = false;
    fields = ",\"result\":" + std::to_string(n);
  } else if (symbol.find("FirmwareUpdaterD") != std::string::npos) {
    U *target = new U(23, 42, &l);
    calls.clear();
    lifecycle = true;
    objectPointer = target;
    original<void (*)(U *)>(symbol.c_str())(target);
    lifecycle = false;
    if (symbol.find("D0") == std::string::npos)
      ::operator delete(target);
  } else if (symbol.find("Surface") != std::string::npos) {
    parameterInfo.tag = val("tag");
    CaptureParam param;
    parameter = &param;
    auto *c = new Presonus::Surface::FirmwareUpdateComponent;
    presonus::surface_update::ConstructionAccess::setup(*c);
    workerPointer = presonus::surface_update::ConstructionAccess::worker(*c);
    calls.clear();
    if (symbol.find("paramChanged") != std::string::npos) {
      original<void (*)(Presonus::Surface::FirmwareUpdateComponent *,
                        Core::Portable::Parameter *, int)>(symbol.c_str())(
          c, &param, val("msg", 2));
    } else if (symbol.find("FirmwareUpdateComponentD") != std::string::npos) {
      lifecycle = true;
      objectPointer = c;
      original<void (*)(Presonus::Surface::FirmwareUpdateComponent *)>(
          symbol.c_str())(c);
      lifecycle = false;
      if (symbol.find("D0") == std::string::npos)
        ::operator delete(c);
      c = nullptr;
    } else {
      allocations = true;
      original<void (*)(Presonus::Surface::FirmwareUpdateComponent *)>(
          "_ZN8Presonus7Surface23FirmwareUpdateComponent8doUpdateEv")(c);
      allocations = false;
      assert(queued);
      if (symbol.find("UpgradeTask") != std::string::npos) {
        calls.clear();
        if (symbol.find("4work") != std::string::npos) {
          taskRun = true;
          queued->work();
          taskRun = false;
        } else {
          lifecycle = true;
          objectPointer = queued;
          if (symbol.find("D0") != std::string::npos) {
            delete queued;
            queued = nullptr;
          } else {
            queued->~BackgroundTask();
            lifecycle = false;
            ::operator delete(queued);
            queued = nullptr;
          }
          lifecycle = false;
        }
      }
      if (queued) {
        delete queued;
        queued = nullptr;
      }
    }
    if (c) {
      lifecycle = false;
      delete c;
    }
  } else {
    std::cerr << "unsupported " << symbol;
    return 3;
  }
  std::cout << "{\"calls\":[";
  for (std::size_t i = 0; i < calls.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << calls[i];
  }
  std::cout << ']' << fields << "}\n";
}

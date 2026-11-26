#include "core/portable/coreparaminfo.h"
#include "presonus/surface/WifiSetupComponent.hpp"
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>
using Ui = Presonus::Surface::WifiSetupComponent;
using Manager = Presonus::WIFIManager;
using Param = Core::Portable::Parameter;
namespace presonus::surface {
struct WifiSetupAccess {
  static void text(Ui &ui, const char *s) { ui.observedD8 = s; }
  static const char *text(const Ui &ui) { return ui.observedD8.str(); }
  static int selected(const Ui &ui) { return ui.state.selected; }
  static int offset(const Ui &ui) { return ui.state.listOffset; }
};
} // namespace presonus::surface
static std::vector<std::vector<std::string>> events;
static std::vector<Core::Portable::ParamInfo> infos;
static bool observe = false, captureQueue = true;
static int providerDepth = 0;
static bool feedbackObserved = false;
static void *watched = nullptr;
static bool deleted = false;
static std::vector<void *> parameterPointers;
static int parameterDeletes = 0;
void operator delete(void *p) noexcept {
  if (p == watched)
    deleted = true;
  for (auto &q : parameterPointers)
    if (p && p == q) {
      ++parameterDeletes;
      q = nullptr;
      break;
    }
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { operator delete(p); }
struct Environment : presonus::network::WiFiEnvironment {
  std::atomic<int> commands{0};
  int command(const char *) override {
    ++commands;
    return 0;
  }
  bool exists(const char *) override { return false; }
  void remove(const char *) override {}
  bool read(const char *, std::string &) override { return false; }
  bool write(const char *, const std::string &) override { return false; }
  bool pipe(const char *, std::string &) override { return false; }
  void sleep(unsigned) override {}
  long long milliseconds() override { return 0; }
  std::string tempDirectory() override { return "temp/wifi-ui"; }
  std::vector<std::pair<std::string, std::string>> addresses() override {
    return {{"wlan0", "192.0.2.5"}};
  }
};
struct UiBoundary : presonus::surface::WifiSetupUi {
  void startPasswordInput(Param *, const char *, const void *) override {}
};
extern "C" void
realPage(Presonus::PageComponent *, const char *, const char *,
         int) asm("__real__ZN8Presonus13PageComponentC2EPKcS2_i");
extern "C" void
wrapPage(Presonus::PageComponent *, const char *, const char *,
         int) asm("__wrap__ZN8Presonus13PageComponentC2EPKcS2_i");
extern "C" void wrapPage(Presonus::PageComponent *p, const char *n,
                         const char *f, int tag) {
  if (observe)
    events.push_back(
        {"page-construct", n ? n : "", f ? f : "", std::to_string(tag)});
  realPage(p, n, f, tag);
}
extern "C" void realTimer(Presonus::DelayTimer *,
                          float) asm("__real__ZN8Presonus10DelayTimerC1Ef");
extern "C" void wrapTimer(Presonus::DelayTimer *,
                          float) asm("__wrap__ZN8Presonus10DelayTimerC1Ef");
extern "C" void wrapTimer(Presonus::DelayTimer *p, float f) {
  if (observe)
    events.push_back({"timer-construct", std::to_string(f)});
  realTimer(p, f);
  if (presonus::timing::DelayTimerAccess::get(*p).duration != 10000)
    std::abort();
}
extern "C" void
realTimerD(Presonus::DelayTimer *) asm("__real__ZN8Presonus10DelayTimerD1Ev");
extern "C" void
wrapTimerD(Presonus::DelayTimer *) asm("__wrap__ZN8Presonus10DelayTimerD1Ev");
extern "C" void wrapTimerD(Presonus::DelayTimer *p) {
  if (observe)
    events.push_back({"timer-destroy"});
  realTimerD(p);
}
extern "C" void
realAdd(Core::Portable::ParamList *, const Core::Portable::ParamInfo *, int,
        bool) asm("__real__ZN4Core8Portable9ParamList3addEPKNS0_9ParamInfoEib");
extern "C" void
wrapAdd(Core::Portable::ParamList *, const Core::Portable::ParamInfo *, int,
        bool) asm("__wrap__ZN4Core8Portable9ParamList3addEPKNS0_9ParamInfoEib");
extern "C" void wrapAdd(Core::Portable::ParamList *p,
                        const Core::Portable::ParamInfo *data, int count,
                        bool own) {
  if (observe) {
    events.push_back(
        {"parameters", std::to_string(count), std::to_string(own)});
    for (int i = 0; i < count; ++i)
      infos.push_back(data[i]);
  }
  ++providerDepth;
  realAdd(p, data, count, own);
  --providerDepth;
}
extern "C" void realFeedback(Param *, bool) asm(
    "__real__ZN4Core8Portable9Parameter17setFeedbackNeededEb");
extern "C" void wrapFeedback(Param *, bool) asm(
    "__wrap__ZN4Core8Portable9Parameter17setFeedbackNeededEb");
extern "C" void wrapFeedback(Param *p, bool b) {
  if (observe && !providerDepth)
    events.push_back(
        {"feedback", std::to_string(p->getTag()), std::to_string(b)});
  if (!providerDepth && p->getTag() == 0 && b)
    feedbackObserved = true;
  realFeedback(p, b);
}
extern "C" void
realValue(Core::Portable::NumericParam *, float,
          bool) asm("__real__ZN4Core8Portable12NumericParam8setValueEfb");
extern "C" void
wrapValue(Core::Portable::NumericParam *, float,
          bool) asm("__wrap__ZN4Core8Portable12NumericParam8setValueEfb");
extern "C" void wrapValue(Core::Portable::NumericParam *p, float v, bool edit) {
  if (observe && !providerDepth)
    events.push_back({"setValue", std::to_string(p->getTag()),
                      std::to_string(static_cast<int>(v)),
                      std::to_string(edit)});
  realValue(p, v, edit);
}
extern "C" void realDelegateAdd(Manager *, Presonus::WIFIManagerDelegate *) asm(
    "__real__ZN8Presonus11WIFIManager11addDelegateEPNS_19WIFIManagerDelegateE");
extern "C" void wrapDelegateAdd(Manager *, Presonus::WIFIManagerDelegate *) asm(
    "__wrap__ZN8Presonus11WIFIManager11addDelegateEPNS_19WIFIManagerDelegateE");
extern "C" void wrapDelegateAdd(Manager *m, Presonus::WIFIManagerDelegate *d) {
  if (observe)
    events.push_back({"delegate-add"});
  realDelegateAdd(m, d);
}
extern "C" void
realDelegateRemove(Manager *, Presonus::WIFIManagerDelegate *) asm(
    "__real__ZN8Presonus11WIFIManager14removeDelegateEPNS_"
    "19WIFIManagerDelegateE");
extern "C" void
wrapDelegateRemove(Manager *, Presonus::WIFIManagerDelegate *) asm(
    "__wrap__ZN8Presonus11WIFIManager14removeDelegateEPNS_"
    "19WIFIManagerDelegateE");
extern "C" void wrapDelegateRemove(Manager *m,
                                   Presonus::WIFIManagerDelegate *d) {
  if (observe)
    events.push_back({"delegate-remove"});
  realDelegateRemove(m, d);
}
extern "C" void realScan(Manager *,
                         bool) asm("__real__ZN8Presonus11WIFIManager6doScanEb");
extern "C" void wrapScan(Manager *,
                         bool) asm("__wrap__ZN8Presonus11WIFIManager6doScanEb");
extern "C" void wrapScan(Manager *m, bool b) {
  if (observe)
    events.push_back({"scan", std::to_string(b)});
  realScan(m, b);
}
extern "C" int
realJoin(Manager *, const char *,
         const char *) asm("__real__ZN8Presonus11WIFIManager6doJoinEPKcS2_");
extern "C" int
wrapJoin(Manager *, const char *,
         const char *) asm("__wrap__ZN8Presonus11WIFIManager6doJoinEPKcS2_");
extern "C" int wrapJoin(Manager *m, const char *a, const char *b) {
  if (observe)
    events.push_back({"join", a, b});
  return realJoin(m, a, b);
}
extern "C" void realComponentD(Core::Portable::Component *) asm(
    "__real__ZN4Core8Portable9ComponentD2Ev");
extern "C" void wrapComponentD(Core::Portable::Component *) asm(
    "__wrap__ZN4Core8Portable9ComponentD2Ev");
extern "C" void wrapComponentD(Core::Portable::Component *p) {
  if (observe)
    events.push_back({"component-destroy"});
  realComponentD(p);
}
static std::vector<Core::Portable::BackgroundTask *> pending;
extern "C" void
realQueue(Core::Portable::BackgroundWorker *,
          Core::Portable::BackgroundTask
              *) asm("__real__ZN4Core8Portable16BackgroundWorker7addTaskEPNS0_"
                     "14BackgroundTaskE");
extern "C" void
wrapQueue(Core::Portable::BackgroundWorker *,
          Core::Portable::BackgroundTask
              *) asm("__wrap__ZN4Core8Portable16BackgroundWorker7addTaskEPNS0_"
                     "14BackgroundTaskE");
template <class T> bool kind(Core::Portable::BackgroundTask *t) {
  static T sample;
  return *reinterpret_cast<void **>(t) == *reinterpret_cast<void **>(&sample);
}
extern "C" void wrapQueue(Core::Portable::BackgroundWorker *w,
                          Core::Portable::BackgroundTask *t) {
  if (!captureQueue) {
    realQueue(w, t);
    return;
  }
  std::string type = kind<Manager::ScanWIFITask>(t)        ? "ScanWIFITask"
                     : kind<Manager::ActiveNetworkTask>(t) ? "ActiveNetworkTask"
                     : kind<Manager::JoinNetworkTask>(t)   ? "JoinNetworkTask"
                                                           : "unknown";
  if (observe)
    events.push_back({"queued", type});
  pending.push_back(t);
}
std::string hex(const char *s) {
  if (!s)
    return "NULL";
  std::string out;
  const char *d = "0123456789abcdef";
  for (unsigned char c : std::string(s)) {
    out += d[c >> 4];
    out += d[c & 15];
  }
  return out;
}
void seed(Manager &m) {
  Core::Vector<Manager::NetworkItem *> list;
  for (auto n : {"Studio", "wifi"}) {
    auto *p = new Manager::NetworkItem;
    p->ssid = n;
    p->flags = "[ESS]";
    p->signal = "75";
    list.add(p);
  }
  m.setNetworkItems(list);
}
int main(int argc, char **argv) {
  static Environment environment;
  static UiBoundary uiBinding;
  presonus::network::setWiFiEnvironmentForTesting(&environment);
  presonus::surface::setWifiSetupUi(&uiBinding);
  auto &m = Manager::instance();
  seed(m);
  std::string op = argv[1];
  if (op == "integration")
    captureQueue = false;
  observe = op == "constructor";
  auto *ui = new Ui("wireless-form", 42);
  int delegateBefore = m.delegateCount();
  bool feedback = feedbackObserved;
  if (op == "textInputFinished") {
    auto *names = Core::Portable::ListParam::cast(ui->getParameterByTag(0));
    names->removeAll();
    names->appendString("Studio");
    auto *button = ui->getParameterByTag(101);
    button->setValue(1, false);
    ui->paramChanged(button, Param::kEdit);
    ui->getParameterByTag(7)->fromString(argv[3], false);
    events.clear();
    observe = true;
    ui->textInputFinished(std::stoi(argv[2]));
  } else if (op == "disconnect") {
    presonus::surface::WifiSetupAccess::text(*ui, "previous");
    auto *list = Core::Portable::ListParam::cast(ui->getParameterByTag(0));
    list->removeAll();
    list->appendString("wifi");
    list->appendString("Studio");
    list->setValue(1, false);
    events.clear();
    observe = true;
    ui->disconnect();
  } else if (op == "destructor") {
    for (int i = 0; i < ui->countParameters(); ++i)
      parameterPointers.push_back(ui->getParameterAt(i));
    events.clear();
    observe = true;
    watched = ui;
    if (std::string(argv[2]) == "D0")
      delete ui;
    else
      ui->~Ui();
    if (deleted)
      events.push_back({"delete-ui"});
  } else if (op == "integration") {
    auto limit = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (environment.commands.load() < 3 &&
           std::chrono::steady_clock::now() < limit)
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    m.terminate();
    seed(m);
    m.setStatusMessage("connected");
    m.setActiveNetwork("Studio");
    m.onIdle();
    char status[64]{}, ssid[64]{}, ip[64]{};
    ui->getParameterByTag(3)->toString(status, 64);
    ui->getParameterByTag(4)->toString(ssid, 64);
    ui->getParameterByTag(9)->toString(ip, 64);
    if (std::string(status) != "connected" || std::string(ssid) != "Studio" ||
        std::string(ip) != "192.0.2.5" ||
        ui->getParameterByTag(8)->getValue() != 0.75f)
      return 10;
    delete ui;
    if (m.delegateCount() != 0)
      return 11;
    std::cout << "real manager/delegate/queue integration passed\n";
    observe = false;
    return 0;
  }
  if (op == "disconnect")
    std::cout << "ACTION " << ui->getParameterByTag(0)->getValue() << ' '
              << hex(presonus::surface::WifiSetupAccess::text(*ui)) << '\n';
  std::cout << "STATE " << delegateBefore << ' ' << m.delegateCount() << ' '
            << parameterDeletes << ' ' << deleted << ' ' << feedback << '\n';
  for (auto &info : infos) {
    std::cout << "INFO " << info.type << ' ' << info.tag << ' '
              << hex(info.name);
    for (float f : {info.minValue, info.maxValue, info.midValue,
                    info.defaultValue, info.deltaValue}) {
      unsigned bits;
      std::memcpy(&bits, &f, 4);
      std::cout << ' ' << bits;
    }
    std::cout << ' ' << info.flags << ' ' << hex(info.unitName) << ' '
              << hex(info.curveName) << ' '
              << (info.stringList ? hex(info.stringList[0]) : "NULL") << ' '
              << hex(info.title) << ' ' << hex(info.shortTitle) << '\n';
  }
  for (auto &row : events) {
    std::cout << row[0];
    for (std::size_t i = 1; i < row.size(); ++i)
      std::cout << ' ' << hex(row[i].c_str());
    std::cout << '\n';
  }
  observe = false;
  if (op != "destructor")
    delete ui;
  for (auto *t : pending)
    delete t;
  m.terminate();
  return 0;
}

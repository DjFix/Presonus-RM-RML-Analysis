#include "presonus/network/WIFIManager.hpp"
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <iostream>
static void *watched = nullptr;
static bool taskDeleted = false;
static void *observedWorker = nullptr;
static bool workerDeleted = false;
static void *itemAllocations[1024]{};
static int itemDeleteCount = 0;
void *operator new(std::size_t size) {
  void *p = std::malloc(size);
  if (!p)
    throw std::bad_alloc();
  if (size == sizeof(Presonus::WIFIManager::NetworkItem))
    for (auto &slot : itemAllocations)
      if (!slot) {
        slot = p;
        break;
      }
  return p;
}

void operator delete(void *p) noexcept {
  for (auto &slot : itemAllocations)
    if (slot == p && p) {
      slot = nullptr;
      ++itemDeleteCount;
      break;
    }
  if (p == watched)
    taskDeleted = true;
  if (p == observedWorker)
    workerDeleted = true;
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { operator delete(p); }
#include <map>
#include <mutex>
#include <new>
#include <sstream>
#include <thread>
using Presonus::WIFIManager;
struct Offline final : presonus::network::WiFiEnvironment {
  std::vector<std::vector<std::string>> trace;
  std::map<std::string, std::string> files;
  std::vector<std::pair<std::string, std::string>> ips;
  bool writeFail = false;
  bool response = false;
  bool filePresent = false;
  bool scriptPipe = false, pipeFail = false;
  long long now = 0;
  bool autoMode = false, recordAutoClock = false;
  std::vector<int> probes, rngValues;
  std::size_t probeIndex = 0, rngIndex = 0;
  std::string pipeData;
  std::vector<int> responses;
  std::size_t nextResponse = 0;
  int command(const char *s) override {
    int result = 0;
    if (autoMode && std::strncmp(s, "ping ", 5) == 0)
      result = probes.at(probeIndex++);
    if (autoMode)
      trace.push_back({"command", s, std::to_string(result)});
    else
      trace.push_back({"command", s});
    if (std::strncmp(s, "wpa_cli ", 8) == 0 && !responses.empty()) {
      filePresent = true;
      response =
          nextResponse < responses.size() ? responses[nextResponse++] : true;
    }
    return result;
  }
  bool exists(const char *p) override {
    return files.empty() ? filePresent || response : files.count(p);
  }
  void remove(const char *s) override { trace.push_back({"remove", s}); }
  bool read(const char *p, std::string &s) override {
    if (!files.empty()) {
      auto i = files.find(p);
      if (i == files.end())
        return false;
      s = i->second;
      return true;
    }
    s = response ? "OK\n" : "FAIL\n";
    return filePresent || response;
  }
  bool write(const char *p, const std::string &text) override {
    if (writeFail)
      return false;
    trace.push_back({"write", p, text});
    return true;
  }
  bool pipe(const char *p, std::string &out) override {
    if (!scriptPipe) {
      trace.push_back({"pipe", p});
      return false;
    }
    trace.push_back({"pipe", p, "r"});
    if (pipeFail)
      return false;
    out = pipeData;
    trace.push_back({"pipe-close"});
    return true;
  }
  void sleep(unsigned n) override {
    trace.push_back({"sleep", std::to_string(n)});
  }
  long long milliseconds() override {
    if (recordAutoClock)
      trace.push_back({"clock-seconds", std::to_string(now / 1000)});
    return now;
  }
  std::string tempDirectory() override { return "temp/wifi"; }
  std::vector<std::pair<std::string, std::string>> addresses() override {
    return ips;
  }
};
static Offline *activeOffline = nullptr;
extern "C" void __real_srand(unsigned);
extern "C" int __real_rand();
extern "C" void __wrap_srand(unsigned seed) {
  if (activeOffline && activeOffline->autoMode)
    activeOffline->trace.push_back({"srand", std::to_string(seed)});
  else
    __real_srand(seed);
}
extern "C" int __wrap_rand() {
  if (activeOffline && activeOffline->autoMode) {
    int value = activeOffline->rngValues.at(activeOffline->rngIndex++);
    activeOffline->trace.push_back({"rand", std::to_string(value)});
    return value;
  }
  return __real_rand();
}
std::vector<int> parseInts(const char *text) {
  std::vector<int> out;
  std::istringstream in(text);
  std::string piece;
  while (std::getline(in, piece, ','))
    if (!piece.empty())
      out.push_back(std::stoi(piece));
  return out;
}
extern "C" void realTerminate(void *) asm(
    "__real__ZN4Core8Portable16BackgroundWorker9terminateEv");
extern "C" void wrapTerminate(void *p) asm(
    "__wrap__ZN4Core8Portable16BackgroundWorker9terminateEv");
extern "C" void wrapTerminate(void *p) {
  observedWorker = p;
  realTerminate(p);
  if (activeOffline)
    activeOffline->trace.push_back({"terminate"});
}
static bool captureQueues = false;
static bool captureQueuePayload = false;
template <class T> bool isTaskType(Core::Portable::BackgroundTask *p) {
  static T sample;
  return *reinterpret_cast<void **>(p) == *reinterpret_cast<void **>(&sample);
}
extern "C" void realAddTask(void *, Core::Portable::BackgroundTask *) asm(
    "__real__ZN4Core8Portable16BackgroundWorker7addTaskEPNS0_"
    "14BackgroundTaskE");
extern "C" void wrapAddTask(void *, Core::Portable::BackgroundTask *) asm(
    "__wrap__ZN4Core8Portable16BackgroundWorker7addTaskEPNS0_"
    "14BackgroundTaskE");
extern "C" void wrapAddTask(void *p, Core::Portable::BackgroundTask *t) {
  if (!captureQueues) {
    realAddTask(p, t);
    return;
  }
  std::string kind;
  if (isTaskType<WIFIManager::ScanWIFITask>(t))
    kind = "ScanWIFITask";
  else if (isTaskType<WIFIManager::ActiveNetworkTask>(t))
    kind = "ActiveNetworkTask";
  else if (isTaskType<WIFIManager::ReconnectTask>(t))
    kind = "ReconnectTask";
  else if (isTaskType<WIFIManager::DisconnectTask>(t))
    kind = "DisconnectTask";
  else if (isTaskType<WIFIManager::JoinNetworkTask>(t))
    kind = "JoinNetworkTask";
  else if (isTaskType<WIFIManager::ConfigNetworkTask>(t))
    kind = "ConfigNetworkTask";
  else if (isTaskType<WIFIManager::StaticIpFailoverTask>(t))
    kind = "StaticIpFailoverTask";
  std::vector<std::string> row{"queued", kind};
  if (captureQueuePayload && kind == "JoinNetworkTask") {
    auto *join = static_cast<WIFIManager::JoinNetworkTask *>(t);
    row.push_back(join->ssid.str());
    row.push_back(join->key.str());
    row.push_back("[" + std::to_string(join->wep) + ", " +
                  std::to_string(join->encrypted) + "]");
  }
  activeOffline->trace.push_back(row);
}

namespace Presonus {
struct WiFiRecoveryProbe {
  static void deadline(WIFIManager &m, long long value) {
    m.scanDeadline = value;
  }
  static long long deadline(const WIFIManager &m) { return m.scanDeadline; }
  static const Core::Vector<Presonus::WIFIManagerDelegate *> &
  delegates(const WIFIManager &m) {
    return m.delegates;
  }
  static const Core::Vector<WIFIManager::NetworkItem *> &
  items(const WIFIManager &m) {
    return m.items;
  }
};
} // namespace Presonus
static bool observeListCalls = false;
static int providerDepth = 0;
static Core::Portable::Parameter *observedParameters[3]{};
static std::vector<std::vector<std::string>> applicationEvents, providerEvents;
static std::string paramIndex(Core::Portable::Parameter *p) {
  for (int i = 0; i < 3; ++i)
    if (observedParameters[i] == p)
      return std::to_string(i);
  return "unknown";
}
extern "C" void realRemoveAll(Core::Portable::ListParam *) asm(
    "__real__ZN4Core8Portable9ListParam9removeAllEv");
extern "C" void wrapRemoveAll(Core::Portable::ListParam *) asm(
    "__wrap__ZN4Core8Portable9ListParam9removeAllEv");
extern "C" void wrapRemoveAll(Core::Portable::ListParam *p) {
  if (observeListCalls && !providerDepth)
    applicationEvents.push_back({"removeAll", paramIndex(p)});
  ++providerDepth;
  realRemoveAll(p);
  --providerDepth;
}
extern "C" void realAppendString(Core::Portable::ListParam *, const char *) asm(
    "__real__ZN4Core8Portable9ListParam12appendStringEPKc");
extern "C" void wrapAppendString(Core::Portable::ListParam *, const char *) asm(
    "__wrap__ZN4Core8Portable9ListParam12appendStringEPKc");
extern "C" void wrapAppendString(Core::Portable::ListParam *p,
                                 const char *text) {
  if (observeListCalls && !providerDepth)
    applicationEvents.push_back({"append", paramIndex(p), text});
  ++providerDepth;
  realAppendString(p, text);
  --providerDepth;
}
extern "C" void realChanged(Core::Portable::Parameter *) asm(
    "__real__ZN4Core8Portable9Parameter7changedEv");
extern "C" void wrapChanged(Core::Portable::Parameter *) asm(
    "__wrap__ZN4Core8Portable9Parameter7changedEv");
extern "C" void wrapChanged(Core::Portable::Parameter *p) {
  if (observeListCalls && !providerDepth)
    applicationEvents.push_back({"changed", paramIndex(p)});
  ++providerDepth;
  realChanged(p);
  --providerDepth;
}
extern "C" void realRangeChanged(Core::Portable::Parameter *) asm(
    "__real__ZN4Core8Portable9Parameter12rangeChangedEv");
extern "C" void wrapRangeChanged(Core::Portable::Parameter *) asm(
    "__wrap__ZN4Core8Portable9Parameter12rangeChangedEv");
extern "C" void wrapRangeChanged(Core::Portable::Parameter *p) {
  if (observeListCalls && !providerDepth)
    applicationEvents.push_back({"rangeChanged", paramIndex(p)});
  ++providerDepth;
  realRangeChanged(p);
  --providerDepth;
}
struct ObservedList : Core::Portable::ListParam {
  using ListParam::ListParam;
  void setValue(Core::Portable::ParamValue value, bool edit = false) override {
    if (observeListCalls && !providerDepth)
      applicationEvents.push_back({"param-setValue", paramIndex(this),
                                   std::to_string(static_cast<int>(value))});
    ++providerDepth;
    Core::Portable::NumericParam::setValue(value, edit);
    --providerDepth;
  }
};
struct ParameterObserver : Core::Portable::ParamObserverBase {
  void paramChanged(Core::Portable::Parameter *p, int msg) override {
    providerEvents.push_back({paramIndex(p), std::to_string(msg)});
  }
};
struct IdleDelegate : Presonus::WIFIManagerDelegate {
  int index;
  WIFIManager *expected;
  IdleDelegate(int i, WIFIManager &m) : index(i), expected(&m) {}
  void record(const char *kind, WIFIManager *p) {
    if (p != expected)
      std::abort();
    applicationEvents.push_back(
        {kind, std::to_string(index), "manager",
         std::string(p->stateChangePending() ? "01" : "00") +
             (p->adapterChangePending() ? "01" : "00")});
  }
  void wifiStateChanged(WIFIManager *m) override {
    record("delegate-state", m);
  }
  void wifiAdaptersChanged(WIFIManager *m) override {
    record("delegate-adapters", m);
  }
};
struct SilentDelegate final : Presonus::WIFIManagerDelegate {
  void wifiStateChanged(WIFIManager *) override {}
  void wifiAdaptersChanged(WIFIManager *) override {}
};
struct QueueTask final : WIFIManager::PipeTask {
  std::atomic<int> &worked;
  std::atomic<int> &destroyed;
  QueueTask(std::atomic<int> &w, std::atomic<int> &d)
      : worked(w), destroyed(d) {}
  void work() override {
    WIFIManager::instance().setStatusMessage("queue");
    ++worked;
  }
  ~QueueTask() override { ++destroyed; }
};
void hex(const std::string &s) {
  const char *d = "0123456789abcdef";
  for (unsigned char c : s)
    std::cout << d[c >> 4] << d[c & 15];
  std::cout << '\n';
}
int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  static Offline offline;
  activeOffline = &offline;
  presonus::network::setWiFiEnvironmentForTesting(&offline);
  auto &m = WIFIManager::instance();
  m.onIdle();
  std::string op = argv[1];
  const char *value =
      argc > 2 && std::strcmp(argv[2], "<NULL>") ? argv[2] : nullptr;
  if (op == "providerQueue") {
    std::atomic<int> worked{0}, destroyed{0};
    for (int i = 0; i < 3; ++i)
      m.addTask(new QueueTask(worked, destroyed));
    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (destroyed.load() != 3 && std::chrono::steady_clock::now() < deadline)
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    m.terminate();
    if (worked != 3 || destroyed != 3 ||
        std::strcmp(m.statusMessage(), "Store to Join") != 0)
      return 10;
    std::cout << "CCL queue work=3 destroy=3 status=Store to Join\n";
  } else if (op == "repeatSetterPositive") {
    bool status = std::strcmp(argv[3], "setStatusMessage") == 0;
    if (status)
      m.setStatusMessage(value);
    else
      m.setActiveNetwork(value);
    m.onIdle();
    if (status)
      m.setStatusMessage(value);
    else
      m.setActiveNetwork(value);
    hex(status ? m.statusMessage() : m.activeNetwork());
    std::cout << m.stateChangePending() << '\n';
  } else if (op == "setStatusMessage") {
    m.setStatusMessage(value);
    hex(m.statusMessage());
    std::cout << m.stateChangePending() << '\n';
  } else if (op == "setActiveNetwork") {
    m.setActiveNetwork(value);
    hex(m.activeNetwork());
    std::cout << m.stateChangePending() << '\n';
  } else if (op == "setStaticIp") {
    m.setStaticIp(value);
    hex(m.staticIP());
    std::cout << m.stateChangePending() << '\n';
  } else if (op == "isActive") {
    m.setActiveNetwork(value);
    std::cout << m.isActive() << '\n';
  } else if (op == "doCommand") {
    auto *t = new WIFIManager::ReconnectTask;
    bool r = t->doCommand(value, std::stoi(argv[3]));
    std::cout << r << '\n';
    for (auto &x : offline.trace) {
      std::cout << x[0] << ' ';
      hex(x[1]);
    }
  } else if (op == "ReconnectTask" || op == "DisconnectTask") {
    offline.response = std::stoi(argv[2]) != 0;
    WIFIManager::PipeTask *t = op == "ReconnectTask"
                                   ? static_cast<WIFIManager::PipeTask *>(
                                         new WIFIManager::ReconnectTask)
                                   : new WIFIManager::DisconnectTask;
    t->work();
    std::cout << m.lastError() << '\n';
    hex(m.statusMessage());
  } else {
    if (op == "configAutoPositive") {
      offline.autoMode = true;
      offline.recordAutoClock = true;
      offline.now = 1000000;
      offline.probes = parseInts(argv[2]);
      offline.rngValues = parseInts(argv[3]);
      auto *task = new WIFIManager::ConfigNetworkTask;
      task->interfaceName = "eth0";
      task->ip = "169.254.1.77";
      task->subnet = "old-mask";
      task->gateway = "old-gateway";
      task->autoAssign = true;
      task->config();
      offline.recordAutoClock = false;
      std::cout << "0\n";
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex("");
      std::cout << "AUTO\t" << task->ip.str() << '\t' << task->subnet.str()
                << '\t' << task->gateway.str() << '\t'
                << (task->dynamic ? "01" : "00")
                << (task->autoAssign ? "01" : "00") << '\t'
                << (offline.probes.size() - offline.probeIndex) << '\t'
                << (offline.rngValues.size() - offline.rngIndex) << '\n';
    } else if (op == "delegatePositive") {
      SilentDelegate first, second, unknown;
      Presonus::WIFIManagerDelegate *ids[] = {&first, &second, &unknown};
      for (auto *p : {&first, &first, &second})
        m.addDelegate(p);
      std::string scenario = argv[2];
      if (scenario == "remove_first")
        m.removeDelegate(&first);
      else if (scenario == "remove_last")
        m.removeDelegate(&second);
      else if (scenario == "remove_unknown")
        m.removeDelegate(&unknown);
      else if (scenario == "remove_all") {
        m.removeDelegate(&first);
        m.removeDelegate(&first);
        m.removeDelegate(&second);
      }
      std::cout << "0\n";
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex("");
      std::cout << "DELEGATES";
      const auto &delegates = Presonus::WiFiRecoveryProbe::delegates(m);
      for (int i = 0; i < delegates.count(); ++i) {
        int index = 0;
        while (index < 3 && delegates[i] != ids[index])
          ++index;
        std::cout << '\t' << index;
      }
      std::cout << '\n';
    } else if (op == "updateListPositive" || op == "setNetworkItemsPositive" ||
               op == "onIdlePositive") {
      if (op == "updateListPositive") {
        Core::Vector<WIFIManager::NetworkItem *> items;
        int count = std::strcmp(argv[2], "populated") == 0 ? 3 : 1;
        const char *labels[] = {"Studio Main", "Guest", "Legacy"};
        const char *flags[] = {"[WPA2-PSK-CCMP][ESS]", "[ESS]", "[WEP][ESS]"};
        for (int i = 0; i < count; ++i) {
          auto *item = new WIFIManager::NetworkItem;
          item->ssid = labels[i];
          item->signal.appendFormat("%d", -40 - i);
          item->flags = count == 1 ? "[ESS]" : flags[i];
          items.add(item);
        }
        m.setNetworkItems(items);
        Core::Portable::ParamInfo info{};
        info.type = Core::Portable::ParamInfo::kList;
        ObservedList names(info), levels(info), icons(info);
        ParameterObserver observer;
        Core::Portable::ListParam *params[] = {&names, &levels, &icons};
        for (int i = 0; i < 3; ++i) {
          params[i]->appendString("OLD");
          observedParameters[i] = params[i];
          params[i]->addObserver(&observer);
        }
        observeListCalls = true;
        m.updateList(&names, &levels, &icons, false);
        observeListCalls = false;
        std::cout << "0\n";
        hex(m.statusMessage());
        hex(m.activeNetwork());
        hex("");
        for (auto *p : params) {
          std::cout << "LIST";
          for (int i = 0; i < p->getStringCount(); ++i) {
            std::cout << '\t';
            const char *digits = "0123456789abcdef";
            for (unsigned char c : std::string(p->getStringAt(i)))
              std::cout << digits[c >> 4] << digits[c & 15];
          }
          std::cout << '\n';
          p->removeObserver(&observer);
        }
        // Actual pinned CCL may emit extra internal notifications on setMax.
        // All observer messages are retained separately from application calls.
      } else if (op == "setNetworkItemsPositive") {
        auto *previous = new WIFIManager::NetworkItem;
        previous->ssid = "Previous";
        Core::Vector<WIFIManager::NetworkItem *> old;
        old.add(previous);
        m.setNetworkItems(old);
        Core::Vector<WIFIManager::NetworkItem *> fresh;
        fresh.setDelta(17);
        auto *z = new WIFIManager::NetworkItem;
        z->bssid = "b";
        z->ssid = "Zulu";
        fresh.add(z);
        auto *a = new WIFIManager::NetworkItem;
        a->bssid = "a";
        a->ssid = "Alpha";
        fresh.add(a);
        int deletedBefore = itemDeleteCount;
        m.setNetworkItems(fresh);
        const auto &published = Presonus::WiFiRecoveryProbe::items(m);
        bool aliases = published.count() == fresh.count();
        for (int i = 0; i < published.count(); ++i)
          aliases = aliases && published[i] == fresh[i];
        std::cout << "0\n";
        hex(m.statusMessage());
        hex(m.activeNetwork());
        hex("");
        std::cout << "META\t" << published.getDelta() << '\t' << fresh.count()
                  << '\t' << aliases << '\t' << m.stateChangePending() << '\t'
                  << (itemDeleteCount - deletedBefore) << '\n';
        for (int i = 0; i < published.count(); ++i) {
          auto *p = published[i];
          std::cout << "ITEM\t";
          for (auto *t : {p->bssid.str(), p->frequency.str(), p->signal.str(),
                          p->flags.str(), p->ssid.str()}) {
            const char *d = "0123456789abcdef";
            for (unsigned char c : std::string(t))
              std::cout << d[c >> 4] << d[c & 15];
            std::cout << '\t';
          }
          std::cout << '\n';
        }
      } else {
        captureQueues = true;
        int dirty = std::stoi(argv[2]), adapters = std::stoi(argv[3]);
        if (dirty) {
          m.setStatusMessage("changed");
          m.resetStatusMsg();
        }
        if (adapters)
          m.adaptersChanged();
        Presonus::WiFiRecoveryProbe::deadline(m, std::stoll(argv[4]));
        offline.now = std::stoll(argv[5]) / 1000000;
        IdleDelegate first(0, m), second(1, m);
        m.addDelegate(&first);
        m.addDelegate(&second);
        m.onIdle();
        std::cout << "0\n";
        hex(m.statusMessage());
        hex(m.activeNetwork());
        hex("");
        std::cout << "META\t" << (m.stateChangePending() ? "01" : "00")
                  << (m.adapterChangePending() ? "01" : "00") << '\t'
                  << Presonus::WiFiRecoveryProbe::deadline(m) << '\n';
      }
      for (auto &row : applicationEvents) {
        std::cout << "EVENT\t" << row[0];
        for (std::size_t i = 1; i < row.size(); ++i) {
          std::cout << '\t';
          const char *d = "0123456789abcdef";
          for (unsigned char c : row[i])
            std::cout << d[c >> 4] << d[c & 15];
        }
        std::cout << '\n';
      }
      for (auto &row : providerEvents) {
        std::cout << "PROVIDER\t" << row[0] << '\t' << row[1] << '\n';
      }
    } else if (op == "getWifiIPPositive" || op == "getEthernetIPPositive" ||
               op == "getIPPositive") {
      m.setActiveNetwork(argv[2]);
      for (int i = 3; i + 1 < argc; i += 2)
        offline.ips.emplace_back(argv[i], argv[i + 1]);
      const char *result = op == "getWifiIPPositive"       ? m.getWifiIP()
                           : op == "getEthernetIPPositive" ? m.getEthernetIP()
                                                           : m.getIP();
      hex(result);
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex("");
    } else if (op == "doJoinPositive") {
      captureQueues = true;
      captureQueuePayload = true;
      auto *item = new WIFIManager::NetworkItem;
      item->ssid = "Studio";
      item->flags = argv[2];
      Core::Vector<WIFIManager::NetworkItem *> items;
      items.add(item);
      m.setNetworkItems(items);
      std::cout << m.doJoin("Studio", "Password") << '\n';
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex("");
    } else if (op == "failoverPositive") {
      offline.scriptPipe = true;
      offline.pipeData = argv[2];
      offline.writeFail = std::stoi(argv[3]);
      offline.pipeFail = std::stoi(argv[4]);
      auto *task = new WIFIManager::StaticIpFailoverTask;
      task->interfaceName = "eth0";
      task->ip = "169.254.2.3";
      task->work();
      std::cout << "0\n";
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex("");
      std::cout << m.adapterChangePending() << " 0\n";
    } else if (op == "scanPositive" || op == "activePositive" ||
               op == "isEthernetPositive") {
      offline.files["temp/wifi/scan.txt"] = argv[2];
      if (op != "scanPositive") {
        offline.files["temp/wifi/ifconfig_tmp.txt"] = argv[3];
        for (int i = 4; i + 1 < argc; i += 2)
          offline.ips.emplace_back(argv[i], argv[i + 1]);
      }
      int result = 0;
      if (op == "scanPositive")
        (new WIFIManager::ScanWIFITask)->work();
      else if (op == "activePositive")
        (new WIFIManager::ActiveNetworkTask)->work();
      else
        result = (new WIFIManager::ActiveNetworkTask)->isEthernet();
      std::cout << result << '\n';
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex("");
      Core::Portable::ParamInfo info{};
      info.type = Core::Portable::ParamInfo::kList;
      Core::Portable::ListParam names(info);
      m.updateList(&names, nullptr, nullptr, true);
      for (int i = 0; i < names.getStringCount(); ++i) {
        auto *p = m.find(names.getStringAt(i));
        if (!p)
          return 11;
        std::cout << "ITEM\t";
        for (auto *text : {p->bssid.str(), p->frequency.str(), p->signal.str(),
                           p->flags.str(), p->ssid.str()}) {
          const char *d = "0123456789abcdef";
          for (unsigned char c : std::string(text))
            std::cout << d[c >> 4] << d[c & 15];
          std::cout << '\t';
        }
        std::cout << '\n';
      }
      for (int i = 0; i < itemDeleteCount; ++i)
        offline.trace.push_back({"delete", "owned"});
    } else if (op == "managerDestructor") {
      auto *local = new WIFIManager;
      auto state = std::string(local->statusMessage());
      auto active = std::string(local->activeNetwork());
      watched = local;
      if (std::string(argv[2]).find("D0Ev") != std::string::npos)
        delete local;
      else
        local->~WIFIManager();
      if (workerDeleted)
        offline.trace.push_back({"worker-delete"});
      if (taskDeleted)
        offline.trace.push_back({"delete", "0"});
      std::cout << "0\n";
      hex(state);
      hex(active);
      hex("");
    } else if (op == "reconnect" || op == "disconnect" || op == "probeEth0" ||
               op == "addTask" || op == "doScan" || op == "resetNetwork" ||
               op == "configNetwork" || op == "doJoin" || op == "updateList" ||
               op == "setNetworkItems" || op == "addDelegate" ||
               op == "removeDelegate" || op == "isEthernet" ||
               op == "configWork") {
      captureQueues = true;
      int result = 0;
      SilentDelegate delegate;
      if (op == "reconnect")
        m.reconnect();
      else if (op == "disconnect")
        m.disconnect();
      else if (op == "probeEth0")
        m.probeEth0();
      else if (op == "addTask")
        m.addTask(new WIFIManager::ReconnectTask);
      else if (op == "doScan")
        m.doScan(true);
      else if (op == "resetNetwork")
        result = m.resetNetwork("test", "test", true);
      else if (op == "configNetwork")
        m.configNetwork("test", "test", "test", "test", false, false);
      else if (op == "doJoin")
        result = m.doJoin("test", "test");
      else if (op == "updateList")
        m.updateList(nullptr, nullptr, nullptr, false);
      else if (op == "setNetworkItems") {
        Core::Vector<WIFIManager::NetworkItem *> empty;
        m.setNetworkItems(empty);
      } else if (op == "addDelegate")
        m.addDelegate(&delegate);
      else if (op == "removeDelegate")
        m.removeDelegate(&delegate);
      else if (op == "isEthernet")
        result = (new WIFIManager::ActiveNetworkTask)->isEthernet();
      else {
        offline.writeFail = true;
        (new WIFIManager::ConfigNetworkTask)->work();
      }
      std::cout << result << '\n';
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex("");
      std::cout << m.adapterChangePending() << ' ' << m.delegateCount() << '\n';
    } else if (op == "joinWork") {
      auto *t = new WIFIManager::JoinNetworkTask;
      t->ssid = "Test SSID";
      t->key = "Test key";
      t->wep = std::stoi(argv[2]);
      t->encrypted = std::stoi(argv[3]);
      for (char c : std::string(argv[4]))
        offline.responses.push_back(c == '1');
      t->work();
      std::cout << m.lastError() << '\n';
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex("");
    } else if (op == "constructor") {
      std::cout << "0\n";
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex(m.staticIP());
      hex(m.scratchFile());
    } else if (op == "hasFlag") {
      WIFIManager::NetworkItem item;
      item.flags = argv[3];
      std::cout << item.hasFlag(value) << '\n';
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex("");
    } else if (op == "config") {
      auto *t = new WIFIManager::ConfigNetworkTask;
      t->interfaceName = "eth0";
      t->ip = "10.0.0.2";
      t->gateway = argv[3];
      t->dynamic = std::stoi(argv[2]);
      offline.writeFail = std::stoi(argv[4]);
      t->config();
      std::cout << "0\n";
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex(t->subnet.str());
    } else if (op == "destructor") {
      std::string n = argv[2];
      WIFIManager::PipeTask *t = nullptr;
      if (n.find("12ScanWIFITask") != std::string::npos)
        t = new WIFIManager::ScanWIFITask;
      else if (n.find("17ActiveNetworkTask") != std::string::npos)
        t = new WIFIManager::ActiveNetworkTask;
      else if (n.find("17ConfigNetworkTask") != std::string::npos)
        t = new WIFIManager::ConfigNetworkTask;
      else if (n.find("20StaticIpFailoverTask") != std::string::npos)
        t = new WIFIManager::StaticIpFailoverTask;
      else if (n.find("15JoinNetworkTask") != std::string::npos)
        t = new WIFIManager::JoinNetworkTask;
      else if (n.find("14DisconnectTask") != std::string::npos)
        t = new WIFIManager::DisconnectTask;
      else
        t = new WIFIManager::ReconnectTask;
      m.setStatusMessage("changed");
      watched = t;
      if (n.find("D0Ev") != std::string::npos)
        delete t;
      else
        t->~PipeTask();
      if (taskDeleted)
        offline.trace.push_back({"delete", "0"});
      std::cout << "0\n";
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex("");
    } else {
      m.setStatusMessage("changed");
      unsigned long long result = 0;
      const char *resultText = nullptr;
      if (op == "resetStatusMsg")
        m.resetStatusMsg();
      else if (op == "adaptersChanged")
        m.adaptersChanged();
      else if (op == "doAdHoc")
        result = m.doAdHoc("test-status");
      else if (op == "find")
        result = m.find("test-status") != nullptr;
      else if (op == "terminate")
        m.terminate();
      else if (op == "onIdle")
        m.onIdle();
      else if (op == "getWifiIP")
        resultText = m.getWifiIP();
      else if (op == "getEthernetIP")
        resultText = m.getEthernetIP();
      else if (op == "getIP")
        resultText = m.getIP();
      else {
        auto *t = new WIFIManager::ActiveNetworkTask;
        if (op == "setNone")
          t->setNone();
        else if (op == "setStatus")
          t->setStatus("test-status");
        else if (op == "pipeOK")
          result = t->pipeOK(-1);
        else if (op == "ActiveNetworkTask")
          t->work();
        else if (op == "ScanWIFITask")
          (new WIFIManager::ScanWIFITask)->work();
        else if (op == "StaticIpFailoverTask")
          (new WIFIManager::StaticIpFailoverTask)->work();
        else
          return 3;
      }
      if (resultText)
        hex(resultText);
      else
        std::cout << result << '\n';
      hex(m.statusMessage());
      hex(m.activeNetwork());
      hex("");
    }
    for (auto &line : offline.trace) {
      std::cout << line[0];
      for (std::size_t i = 1; i < line.size(); ++i) {
        std::cout << '\t';
        const char *digits = "0123456789abcdef";
        for (unsigned char c : line[i])
          std::cout << digits[c >> 4] << digits[c & 15];
      }
      std::cout << '\n';
    }
  }
  activeOffline = nullptr;
  return 0;
}

#include "presonus/mixer/AVBCascadeManager.hpp"
#include "presonus/reconstruction200/large02_w04.hpp"
#include "presonus/uc/NetworkItem.hpp"
#include "presonus/uc/client_implementation.hpp"
#include "presonus/uc/client_typed_origins.hpp"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/mutable_message_event.hpp"
#include <bit>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>
#include <vector>
namespace {
std::vector<std::string> trace;
bool recording = false;
Core::Portable::Parameter *observedParameter = nullptr;
Core::Portable::IParamObserver *observedObserver = nullptr;
void *deleting = nullptr;
const Core::IO::Buffer *eventBuffer = nullptr;
const Presonus::UC::Event *lastSentHeader = nullptr;
int concreteManagerResult = -1;
const Core::Portable::AttributeValue *targetAttribute = nullptr;
std::string serialized;
unsigned lastRouteA = 0, lastRouteB = 0;
void emit(std::string s) {
  if (recording)
    trace.push_back(std::move(s));
}
std::string bit(float x) { return std::to_string(std::bit_cast<unsigned>(x)); }
const Core::Portable::ParamInfo testInfo =
    PARAM_FLOAT(1, "value", -100, 100, 0, 1, nullptr, nullptr, 0, 0);
struct Param : Core::Portable::NumericParam {
  std::string label;
  Param(const char *s, float v) : NumericParam(testInfo), label(s) {
    NumericParam::setValue(v, false);
  }
  float getValue() const override {
    emit("[\"value\",\"" + label + "\"]");
    return NumericParam::getValue();
  }
  void setValue(float v, bool edit = false) override {
    emit("[\"set\"," + bit(v) + "," + std::to_string(edit) + "]");
    NumericParam::setValue(v, edit);
  }
  int observers() const { return observerList.count(); }
};
struct CascadeBoundary : presonus::mixer::CascadeBoundary {
  Presonus::UC::NetworkItem *last = nullptr;
  bool flag = false, present = true, changed = false;
  int selects = 0, updates = 0;
  void select(Presonus::UC::NetworkItem *p, bool f) override {
    last = p;
    flag = f;
    ++selects;
  }
  bool connectedClientPresent() override { return present; }
  void connectionChanged(bool p) override { changed = p; }
  void updateChannelSelectionSync() override { ++updates; }
};
struct Idle : presonus::mixer::CascadeIdleTarget {
  void onIdle() override { emit("[\"idle\"]"); }
};
struct Connector : presonus::mixer::RemoteMixerConnector {
  void setComponent(Presonus::MixerClientComponentBase *p) override {
    emit("[\"connector\"," + std::to_string(p != nullptr) + "]");
  }
};
struct Child : Core::Portable::Component {
  ~Child() override { emit("[\"baseDestructor\"]"); }
};
} // namespace
void operator delete(void *p) noexcept {
  if (p == deleting && recording)
    emit("[\"delete\",1]");
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
extern "C" void
real_remove(Core::Portable::Parameter *, Core::Portable::IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrap_remove(
    Core::Portable::Parameter *p,
    Core::Portable::IParamObserver
        *o) asm("__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
                "14IParamObserverE");
extern "C" void wrap_remove(Core::Portable::Parameter *p,
                            Core::Portable::IParamObserver *o) {
  emit("[\"removeObserver\"," + std::to_string(p == observedParameter) + "," +
       std::to_string(o == observedObserver) + "]");
  real_remove(p, o);
}
extern "C" void
native_d1(void *) asm("_ZN8Presonus5Mixer21AVBRemoteMixerHandlerD1Ev");
extern "C" void
native_d2(void *) asm("_ZN8Presonus5Mixer21AVBRemoteMixerHandlerD2Ev");
extern "C" void real_debug(const char *,
                           ...) asm("__real__ZN4Core11DebugPrintfEPKcz");
extern "C" void wrap_debug(const char *,
                           ...) asm("__wrap__ZN4Core11DebugPrintfEPKcz");
extern "C" void wrap_debug(const char *fmt, ...) {
  emit("[\"debug\"]");
  char text[4096];
  va_list args;
  va_start(args, fmt);
  std::vsnprintf(text, sizeof(text), fmt, args);
  va_end(args);
  real_debug("%s", text);
}

extern "C" void
real_mc(Presonus::UC::MessageAttributes *,
        const char *) asm("__real__ZN8Presonus2UC17MessageAttributesC1EPKc");
extern "C" void
wrap_mc(Presonus::UC::MessageAttributes *,
        const char *) asm("__wrap__ZN8Presonus2UC17MessageAttributesC1EPKc");
extern "C" void wrap_mc(Presonus::UC::MessageAttributes *p, const char *id) {
  emit("[\"attributes\",\"" + std::string(id) + "\"]");
  real_mc(p, id);
}
extern "C" void real_url(Presonus::UC::MessageAttributes *, const char *) asm(
    "__real__ZN8Presonus2UC17MessageAttributes6setURLEPKc");
extern "C" void wrap_url(Presonus::UC::MessageAttributes *, const char *) asm(
    "__wrap__ZN8Presonus2UC17MessageAttributes6setURLEPKc");
extern "C" void wrap_url(Presonus::UC::MessageAttributes *p, const char *url) {
  emit("[\"url\",\"" + std::string(url) + "\"]");
  real_url(p, url);
}
extern "C" Core::Portable::Attribute &real_lookup(
    Core::Portable::Attributes *,
    const char *) asm("__real__ZN4Core8Portable10Attributes11lookupOrAddEPKc");
extern "C" Core::Portable::Attribute &wrap_lookup(
    Core::Portable::Attributes *,
    const char *) asm("__wrap__ZN4Core8Portable10Attributes11lookupOrAddEPKc");
extern "C" Core::Portable::Attribute &wrap_lookup(Core::Portable::Attributes *p,
                                                  const char *key) {
  auto &a = real_lookup(p, key);
  if (std::string(key) == "AVBSceneSlot" ||
      std::string(key) == "AVBMComponentID" ||
      std::string(key) == "presetMuteGroupIndex") {
    targetAttribute = &a;
    emit("[\"attribute\",\"" + std::string(key) + "\"]");
  }
  return a;
}
extern "C" void
real_int(Core::Portable::AttributeValue *,
         Core::int64) asm("__real__ZN4Core8Portable14AttributeValue3setEx");
extern "C" void
wrap_int(Core::Portable::AttributeValue *,
         Core::int64) asm("__wrap__ZN4Core8Portable14AttributeValue3setEx");
extern "C" void wrap_int(Core::Portable::AttributeValue *p, Core::int64 v) {
  if (p == targetAttribute) {
    auto x = static_cast<std::uint64_t>(v);
    emit("[\"integer\"," + std::to_string(unsigned(x)) + "," +
         std::to_string(unsigned(x >> 32)) + "]");
  }
  real_int(p, v);
}
extern "C" void
real_string(Core::Portable::AttributeValue *, const char *,
            bool) asm("__real__ZN4Core8Portable14AttributeValue3setEPKcb");
extern "C" void
wrap_string(Core::Portable::AttributeValue *, const char *,
            bool) asm("__wrap__ZN4Core8Portable14AttributeValue3setEPKcb");
extern "C" void wrap_string(Core::Portable::AttributeValue *p, const char *v,
                            bool shared) {
  if (p == targetAttribute)
    emit("[\"string\",\"" + std::string(v) + "\"," + std::to_string(shared) +
         "]");
  real_string(p, v, shared);
}
extern "C" void
real_ec(Presonus::UC::MutableMessageEvent *,
        const Presonus::UC::MessageAttributes &, int,
        int) asm("__real__ZN8Presonus2UC19MutableMessageEventC1ERKNS0_"
                 "17MessageAttributesEii");
extern "C" void
wrap_ec(Presonus::UC::MutableMessageEvent *,
        const Presonus::UC::MessageAttributes &, int,
        int) asm("__wrap__ZN8Presonus2UC19MutableMessageEventC1ERKNS0_"
                 "17MessageAttributesEii");
extern "C" void wrap_ec(Presonus::UC::MutableMessageEvent *p,
                        const Presonus::UC::MessageAttributes &a, int type,
                        int hint) {
  emit("[\"event\"," + std::to_string(type) + "," + std::to_string(hint) + "]");
  targetAttribute = nullptr;
  real_ec(p, a, type, hint);
  eventBuffer = &presonus::uc::MutableMessageEventPortAccess::buffer(*p);
}
extern "C" void
real_bd(Core::IO::Buffer *) asm("__real__ZN4Core2IO6BufferD1Ev");
extern "C" void
wrap_bd(Core::IO::Buffer *) asm("__wrap__ZN4Core2IO6BufferD1Ev");
extern "C" void wrap_bd(Core::IO::Buffer *p) {
  if (p == eventBuffer) {
    emit("[\"bufferDestructor\"]");
    eventBuffer = nullptr;
  }
  real_bd(p);
}
extern "C" void real_md(Presonus::UC::MessageAttributes *) asm(
    "__real__ZN8Presonus2UC17MessageAttributesD1Ev");
extern "C" void wrap_md(Presonus::UC::MessageAttributes *) asm(
    "__wrap__ZN8Presonus2UC17MessageAttributesD1Ev");
extern "C" void wrap_md(Presonus::UC::MessageAttributes *p) {
  emit("[\"attributesDestructor\"]");
  real_md(p);
}
extern "C" void *real_component(const Presonus::UC::NetworkItem *) asm(
    "__real__ZNK8Presonus2UC11NetworkItem12getComponentEv");
extern "C" void *wrap_component(const Presonus::UC::NetworkItem *) asm(
    "__wrap__ZNK8Presonus2UC11NetworkItem12getComponentEv");
extern "C" void *wrap_component(const Presonus::UC::NetworkItem *p) {
  emit("[\"getComponent\"]");
  return real_component(p);
}
extern "C" Core::Portable::Parameter *
real_tag(const Core::Portable::Component *,
         int) asm("__real__ZNK4Core8Portable9Component17getParameterByTagEi");
extern "C" Core::Portable::Parameter *
wrap_tag(const Core::Portable::Component *,
         int) asm("__wrap__ZNK4Core8Portable9Component17getParameterByTagEi");
extern "C" Core::Portable::Parameter *
wrap_tag(const Core::Portable::Component *p, int tag) {
  emit("[\"parameterByTag\"," + std::to_string(static_cast<unsigned>(tag)) +
       "]");
  return real_tag(p, tag);
}
extern "C" int
real_send(Presonus::UC::ClientImplementation *, Presonus::UC::Event &) asm(
    "__real__ZN8Presonus2UC20ClientImplementation9sendEventERNS0_5EventE");
extern "C" int
wrap_send(Presonus::UC::ClientImplementation *, Presonus::UC::Event &) asm(
    "__wrap__ZN8Presonus2UC20ClientImplementation9sendEventERNS0_5EventE");
extern "C" int wrap_send(Presonus::UC::ClientImplementation *p,
                         Presonus::UC::Event &event) {
  emit("[\"sendEvent\"]");
  return real_send(p, event);
}
using namespace Presonus::UC;
struct FixtureNetwork : Presonus::UC::NetworkManager {
  presonus::uc::ClientTypedOrigins &origins;
  presonus::uc::NetworkManagerState &configuration;
  FixtureNetwork(presonus::uc::NetworkManagerState &s,
                 presonus::uc::ClientTypedOrigins &o)
      : NetworkManager(s), origins(o), configuration(s) {}
  void onServerAdded(void *,
                     const Presonus::UC::DiscoveryDescriptor &) override {
    std::abort();
  }
  void onServerRemoved(void *) override { std::abort(); }
  void onConnectionError(Presonus::UC::Connection *, bool) override {
    std::abort();
  }
  int unregistered = 0;
  ~FixtureNetwork() {
    if (unregistered != 1)
      std::abort();
  }
  int sendEvent(const Presonus::UC::Event &e, int flags) override {
    if (flags)
      std::abort();
    lastSentHeader = &e;
    lastRouteA = e.routeA;
    lastRouteB = e.routeB;
    const auto *message = origins.get<Presonus::UC::MessageEvent>(&e);
    if (e.type == 0x4a4d) {
      if (!message ||
          &configuration.messageView(configuration.context, e) != message)
        std::abort();
      serialized.assign(static_cast<const char *>(message->data),
                        message->sizeBits);
    }
    concreteManagerResult = NetworkManager::sendEvent(e, flags);
    if (concreteManagerResult != 101)
      std::abort(); // Real empty factory, no test clone provider.
    return concreteManagerResult;
  }
  int startup(unsigned char) override { std::abort(); }
  int shutdown() override { std::abort(); }
  int setPortNumber(unsigned short, unsigned short, int) override {
    std::abort();
  }
  int setLocalName(const char *) override { std::abort(); }
  int setNetworkPriority(int) override { std::abort(); }
  int registerListener(INetworkListener *) override { std::abort(); }
  int unregisterListener(INetworkListener *) override { std::abort(); }
  int registerServer(int &, IEventHandler *, const ServerInfo &, int) override {
    std::abort();
  }
  int unregisterServer(IEventHandler *) override { std::abort(); }
  int updateServer(IEventHandler *) override { std::abort(); }
  int addRemoteServer(int &, const char *, unsigned short, unsigned short, int,
                      const ServerInfo &) override {
    std::abort();
  }
  int removeRemoteServer(int) override { std::abort(); }
  int registerHandler(int &, IEventHandler *) override { std::abort(); }
  int unregisterHandler(IEventHandler *handler) override {
    if (!handler)
      std::abort();
    ++unregistered;
    return NetworkManager::unregisterHandler(handler);
  }
  int sendMulticastEvent(const Event &) override { std::abort(); }
  int setMulticastMapping(int, int, unsigned char, unsigned char) override {
    std::abort();
  }
  int processIdle() override { std::abort(); }
  int getServerContextInfo(ServerContextInfo &, int) override { std::abort(); }
  int addExternalConnection(IConnection *&, IDataChannel *, int, unsigned char,
                            IEventHandler *) override {
    std::abort();
  }
  int updateExternalConnection(IDataChannel *, int) override { std::abort(); }
  int removeExternalConnection(IDataChannel *) override { std::abort(); }
  int rescanAll(unsigned char) override { std::abort(); }
  int resetConnection() override { std::abort(); }
  int addErrorReporter(INetworkErrorReporter *) override { std::abort(); }
  int removeErrorReporter(INetworkErrorReporter *) override { std::abort(); }
  int simulateConnectionErrors() override { std::abort(); }
  int waitForOutgoingEvents(int) override { std::abort(); }
  int suspendNetworkAdapters(unsigned char) override { std::abort(); }
  int isSendingFromExternalConnection(int) override { std::abort(); }
  int handleEvent(void *, const Presonus::UC::Event &) override {
    std::abort();
  }
};
struct FixtureClient : Presonus::UC::ClientImplementation {
  FixtureClient(Presonus::UC::INetworkManager &m)
      : ClientImplementation(presonus::uc::ClientStatePortTag{}, m, 17, 23) {}
  std::uint64_t getSystemTime() const override { std::abort(); }
  void updateLevels(const Presonus::UC::MeterEvent &) override { std::abort(); }
  void receiveEvent(const Presonus::UC::TimeCodeEvent &) override {
    std::abort();
  }
  void receiveEvent(const Presonus::UC::ParamEvent &) override { std::abort(); }
  void receiveEvent(const Presonus::UC::MessageEvent &) override {
    std::abort();
  }
  void receiveEvent(const Presonus::UC::BinaryEvent &) override {
    std::abort();
  }
  void receiveEvent(const Presonus::UC::DebugEvent &) override { std::abort(); }
  void sendAllToServer() override { std::abort(); }
};
struct FixtureComponent : Core::Portable::Component {
  Core::Portable::Component *findChild(const char *name) const override {
    emit("[\"child\",\"" + std::string(name) + "\"]");
    return Component::findChild(name);
  }
};
int main(int argc, char **argv) {
  if (argc != 16)
    return 2;
  int index = std::atoi(argv[1]);
  bool parameter = std::atoi(argv[2]), saved = std::atoi(argv[3]),
       component = std::atoi(argv[4]);
  float value = std::strtof(argv[5], nullptr),
        savedValue = std::strtof(argv[6], nullptr);
  int nc = std::atoi(argv[7]), na = std::atoi(argv[8]),
      msg = std::atoi(argv[9]);
  bool same = std::atoi(argv[10]);
  int arg = std::atoi(argv[11]);
  (void)arg;
  Param p("parameter", value), s("saved", savedValue);
  observedParameter = &p;
  Connector c;
  presonus::mixer::RemoteMixerState state;
  state.activation = parameter ? &p : nullptr;
  state.savedSelection = saved ? &s : nullptr;
  int componentToken = 0;
  state.component =
      component ? reinterpret_cast<Presonus::MixerClientComponentBase *>(
                      &componentToken)
                : nullptr;
  state.connectors.assign(nc, &c);
  state.activators.assign(na, &c);
  if (index == 0) {
    int token = 0;
    Presonus::UC::NetworkItem selected(&token), other(nullptr);
    CascadeBoundary boundary;
    Presonus::Mixer::AVBCascadeManager manager(boundary, &selected);
    std::uint32_t id = 0x12345678;
    manager.sourcePortBindComponentIds({{&token, &id}});
    if (manager.getSlaveId() != id || !manager.isConnected(&selected) ||
        manager.isConnected(&other))
      return 5;
    manager.connect(&other);
    if (boundary.last != &other || !boundary.flag || boundary.selects != 1)
      return 6;
    manager.onNetworkShutdown();
    if (boundary.last || !boundary.flag || boundary.selects != 2)
      return 7;
    manager.onNetworkItemRemoved(&other);
    if (boundary.selects != 2)
      return 8;
    manager.onNetworkItemRemoved(&selected);
    if (boundary.last || boundary.flag || boundary.selects != 3)
      return 9;
    manager.cardConnectionChanged(true);
    if (!manager.sourcePortCardConnected() || !boundary.changed ||
        boundary.updates != 1)
      return 10;
    std::cout << "REGRESSION ok\n";
    return 0;
  }
  if (index == 17) {
    int token = 0;
    Presonus::UC::NetworkItem item(&token);
    CascadeBoundary boundary;
    Presonus::Mixer::AVBCascadeManager manager(boundary, &item);
    int rejected = 0;
    try {
      manager.presetStored("component/path", 1);
    } catch (const std::logic_error &) {
      ++rejected;
    }
    try {
      manager.presetRecalled("component/path", 1);
    } catch (const std::logic_error &) {
      ++rejected;
    }
    try {
      manager.muteGroupStored(1);
    } catch (const std::logic_error &) {
      ++rejected;
    }
    if (rejected != 3 || lastSentHeader)
      return 11;
    std::cout << "ORIGIN_GUARDS ok\n";
    return 0;
  }
  if (index == 1 || index == 5 || index == 11 || index == 12 || index == 13 ||
      index == 14 || index == 15 || index == 16) {
    const bool peer = std::atoi(argv[12]), selected = std::atoi(argv[13]),
               global = std::atoi(argv[14]), found = std::atoi(argv[15]);
    presonus::uc::ClientTypedOrigins origins;
    presonus::uc::EventDispatcherState dispatchState;
    Presonus::UC::EventDispatcher dispatcher(dispatchState);
    presonus::uc::FactoryRegistry registry;
    Presonus::UC::EventFactory factory(registry);
    presonus::uc::NetworkManagerState networkState{dispatcher, factory};
    networkState.context = &origins;
    networkState.messageView = [](void *context,
                                  const Presonus::UC::Event &event)
        -> const Presonus::UC::MessageEvent & {
      auto *view = static_cast<presonus::uc::ClientTypedOrigins *>(context)
                       ->get<Presonus::UC::MessageEvent>(&event);
      if (!view)
        throw std::logic_error("unbound concrete NetworkManager message view");
      return *view;
    };
    FixtureNetwork network(networkState, origins);
    FixtureClient client(network);
    FixtureComponent core;
    int identity = 0;
    if (global) {
      auto *child = new Core::Portable::Component("global");
      if (found) {
        Core::Portable::ParamInfo inf = testInfo;
        inf.tag = arg;
        child->addParameters(&inf, 1, true);
      }
      core.addChild(child);
    }
    Presonus::UC::NetworkItem item(component ? &identity : nullptr);
    CascadeBoundary boundary;
    Idle idle;
    Presonus::Mixer::AVBCascadeManager manager(boundary,
                                               selected ? &item : nullptr);
    manager.sourcePortBindClients({{&identity, &core, &client}});
    manager.sourcePortBindMessageOrigins(origins);
    if (peer)
      manager.sourcePortBindIdle(&idle);
    bool result = false;
    Presonus::UC::Event event{};
    recording = true;
    switch (index) {
    case 1:
      manager.onIdle();
      break;
    case 5:
      result = manager.getConnectedClient() != nullptr;
      break;
    case 11:
      result = manager.getSlaveParam(arg) != nullptr;
      break;
    case 12:
      result = manager.getConnectedClientComponent() != nullptr;
      break;
    case 13:
      manager.sendEvent(event);
      break;
    case 14:
      manager.presetStored("component/path", arg);
      break;
    case 15:
      manager.muteGroupStored(arg);
      break;
    case 16:
      manager.presetRecalled("component/path", arg);
      break;
    }
    recording = false;
    if (lastSentHeader &&
        origins.get<Presonus::UC::MessageEvent>(lastSentHeader))
      std::abort();
    std::cout << "{\"trace\":[";
    for (std::size_t i = 0; i < trace.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << trace[i];
    }
    std::cout << "],\"parameter_present\":" << (parameter ? "true" : "false")
              << ",\"component_present\":" << (component ? "true" : "false");
    if (index == 5 || index == 11 || index == 12)
      std::cout << ",\"result_present\":" << (result ? "true" : "false");
    std::cout << "}\n";
    if (!serialized.empty())
      std::cout << "PAYLOAD " << serialized << "\n";
    if (lastRouteA || lastRouteB)
      std::cout << "ROUTES " << lastRouteA << " " << lastRouteB << "\n";
    if (concreteManagerResult != -1)
      std::cout << "CONCRETE_MANAGER_RESULT " << concreteManagerResult << "\n";
    return 0;
  }
  auto *h = new Presonus::Mixer::AVBRemoteMixerHandler(state);
  observedObserver = h;
  bool dead = false;
  if (index == 7 || index == 9 || index == 10) {
    h->addChild(new Child);
    if (parameter)
      p.addObserver(h);
  }
  recording = true;
  switch (index) {
  case 2:
    h->activate();
    break;
  case 3:
    h->onRestoredSelection();
    break;
  case 4:
    h->paramChanged(same ? static_cast<Core::Portable::Parameter *>(&p) : &s,
                    msg);
    break;
  case 6:
    h->setMixerComponent(state.component);
    break;
  case 7:
    native_d2(h);
    dead = true;
    break;
  case 8:
    h->connect();
    break;
  case 9:
    deleting = h;
    delete h;
    dead = true;
    break;
  case 10:
    native_d1(h);
    dead = true;
    break;
  default:
    return 3;
  }
  recording = false;
  if (dead && parameter && p.observers() != 0)
    return 4;
  // Snapshot only state that outlives the destroyed object.
  std::cout << "{\"trace\":[";
  for (std::size_t i = 0; i < trace.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << trace[i];
  }
  std::cout << "],\"parameter_present\":"
            << (state.activation ? "true" : "false")
            << ",\"component_present\":" << (state.component ? "true" : "false")
            << "}\n";
  if (!dead)
    delete h;
  else if (index != 9)
    ::operator delete(h);
}

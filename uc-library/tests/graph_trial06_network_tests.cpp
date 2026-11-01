#include "presonus/mixer/NetworkSetupComponent.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace Presonus::UC;
namespace {
std::int64_t clockValue;
std::int64_t fixtureClock() { return clockValue; }
const std::array<std::string, 5> names{"", "Alpha", "", std::string(45, 'Z'),
                                       "Outside"};
const std::array<std::string, 5> serials{"", "serial-one", "serial-two",
                                         "serial-three", "outside"};
const std::array<std::string, 5> titles{"", "TitleA", "TitleB", "TitleC",
                                        "TitleD"};
std::string quote(const std::string &s) { return "\"" + s + "\""; }
template <class T> std::string arrayJSON(const T &values) {
  std::string out = "[";
  for (const auto &v : values) {
    if (out.size() > 1)
      out += ',';
    if constexpr (std::is_same_v<typename T::value_type, std::string>)
      out += quote(v);
    else
      out += std::to_string(v);
  }
  return out + ']';
}
class Manager final : public Presonus::UC::INetworkManager {
public:
  std::vector<std::string> &trace;
  explicit Manager(std::vector<std::string> &t) : trace(t) {}
  int handleEvent(void *, const Presonus::UC::Event &) override { return 0; }
  int startup(unsigned char) override { return 0; }
  int shutdown() override { return 0; }
  int setPortNumber(unsigned short, unsigned short, int) override { return 0; }
  int setLocalName(const char *) override { return 0; }
  int setNetworkPriority(int) override { return 0; }
  int registerListener(INetworkListener *) override { return 0; }
  int unregisterListener(INetworkListener *) override { return 0; }
  int registerServer(int &, IEventHandler *, const ServerInfo &, int) override {
    return 0;
  }
  int unregisterServer(IEventHandler *) override { return 0; }
  int updateServer(IEventHandler *) override { return 0; }
  int addRemoteServer(int &, const char *, unsigned short, unsigned short, int,
                      const ServerInfo &) override {
    return 0;
  }
  int removeRemoteServer(int) override { return 0; }
  int registerHandler(int &, IEventHandler *) override { return 0; }
  int unregisterHandler(IEventHandler *) override { return 0; }
  int sendEvent(const Event &, int) override {
    trace.push_back("send");
    return 37;
  }
  int sendMulticastEvent(const Event &) override { return 0; }
  int setMulticastMapping(int, int, unsigned char, unsigned char) override {
    return 0;
  }
  int processIdle() override { return 0; }
  int getServerContextInfo(ServerContextInfo &, int) override { return 0; }
  int addExternalConnection(IConnection *&, IDataChannel *, int, unsigned char,
                            IEventHandler *) override {
    return 0;
  }
  int updateExternalConnection(IDataChannel *, int) override { return 0; }
  int removeExternalConnection(IDataChannel *) override { return 0; }
  int rescanAll(unsigned char) override { return 0; }
  int resetConnection() override { return 0; }
  int addErrorReporter(INetworkErrorReporter *) override { return 0; }
  int removeErrorReporter(INetworkErrorReporter *) override { return 0; }
  int simulateConnectionErrors() override { return 0; }
  int waitForOutgoingEvents(int) override { return 0; }
  int suspendNetworkAdapters(unsigned char) override { return 0; }
  int isSendingFromExternalConnection(int) override { return 0; }
};
class Client final : public ClientImplementation {
public:
  explicit Client(Manager &m)
      : ClientImplementation(presonus::uc::ClientStatePortTag{}, m, 1, 2) {}
  std::uint64_t getSystemTime() const override { return 0; }
  void updateLevels(const MeterEvent &) override {}
  void receiveEvent(const TimeCodeEvent &) override {}
  void receiveEvent(const ParamEvent &) override {}
  void receiveEvent(const MessageEvent &) override {}
  void receiveEvent(const BinaryEvent &) override {}
  void receiveEvent(const DebugEvent &) override {}
  void sendAllToServer() override {}
};
class Services final : public presonus::mixer::NetworkSetupServices {
public:
  mutable std::vector<std::string> trace;
  std::array<int, 5> tokens{};
  int clientToken = 0;
  int arg = 1, type = 0, filter = 0;
  bool hasComponent = true, castOK = true;
  Manager manager{trace};
  mutable Client client{manager};
  NetworkItem *item(int i) {
    return i ? reinterpret_cast<NetworkItem *>(&tokens[i]) : nullptr;
  }
  int id(const NetworkItem &i) const {
    return static_cast<int>(reinterpret_cast<const int *>(&i) - tokens.data());
  }
  void record(const std::string &s) const { trace.push_back(s); }
  int itemKind(const NetworkItem &i) const override {
    return id(i) == arg ? type : 0;
  }
  int itemFilter(const NetworkItem &i) const override {
    return id(i) == arg ? filter : 0;
  }
  const char *itemName(const NetworkItem &i) const override {
    return names[id(i)].c_str();
  }
  const char *itemSerial(const NetworkItem &i) const override {
    return serials[id(i)].c_str();
  }
  void itemTitle(const NetworkItem &i,
                 Core::CStringBuffer<128> &text) const override {
    record("title:" + std::to_string(id(i)));
    text = titles[id(i)].c_str();
  }
  ClientRootComponent *component(const NetworkItem &i) const override {
    record("component:" + std::to_string(id(i)));
    return hasComponent ? reinterpret_cast<ClientRootComponent *>(
                              const_cast<int *>(&clientToken))
                        : nullptr;
  }
  ClientImplementation &eventSender(ClientRootComponent &) const override {
    return client;
  }
  void acquire(NetworkItem &i) override {
    record("acquire:" + std::to_string(id(i)));
  }
  void release(NetworkItem &i, bool b) override {
    record("release:" + std::to_string(id(i)) + ":" + std::to_string(b));
  }
  void *mixerForClient(ClientRootComponent &) override {
    record("cast");
    return castOK ? &clientToken : nullptr;
  }
  void setRemoteMixer(void *m) override {
    record("remote:" + std::to_string(m ? 1 : 0));
  }
  void remoteIdle() override { record("idle"); }
  void restoredSelection() override { record("restored"); }
  void serverParamChanged(Core::Portable::Parameter *p, int msg) override {
    record("base:" + std::to_string(msg) + ":" + std::to_string(p->getTag()));
  }
};
class RangeObserver final : public Core::Portable::ParamObserverBase {
public:
  int ranges = 0;
  void paramChanged(Core::Portable::Parameter *, int m) override {
    if (m == Core::Portable::Parameter::kRangeChanged)
      ++ranges;
  }
};
void run(const std::array<std::int64_t, 17> &c) {
  using namespace Core::Portable;
  Services services;
  services.arg = static_cast<int>(c[2]);
  services.type = static_cast<int>(c[13]);
  services.filter = static_cast<int>(c[14]);
  services.hasComponent = c[11];
  services.castOK = c[12];
  static const char *initialList[] = {"initial"};
  static const ParamInfo infos[] = {
      PARAM_LIST(0, "list", initialList, 0, 0), PARAM_STRING(1, "name", 0),
      PARAM_INT(2, "changed", -100, 100, 0, "", 0, 0, 0),
      PARAM_INT(3, "connected", 0, 1, 0, "", 0, 0, 0)};
  Component parameters;
  parameters.addParameters(infos, 4);
  auto *list = static_cast<ListParam *>(parameters.getParameterByTag(0));
  list->setMin(-100);
  list->setMax(100);
  list->setValue(static_cast<float>(c[10]));
  auto *name = static_cast<StringParam *>(parameters.getParameterByTag(1));
  name->fromString("initial");
  ParamInfo changedInfo = infos[2];
  changedInfo.tag = static_cast<int>(c[9]);
  NumericParam changed(changedInfo);
  static const ParamInfo savedInfo = PARAM_STRING(7, "saved", 0);
  StringParam saved(savedInfo);
  saved.fromString(c[5] ? serials[static_cast<int>(c[15])].c_str() : "");
  std::uint64_t last = static_cast<std::uint64_t>(c[7]);
  clockValue = c[6];
  presonus::mixer::NetworkSetupState state{parameters, services};
  for (int i = 1; i <= c[3]; ++i)
    state.items.add(services.item(i));
  state.selected = services.item(static_cast<int>(c[1]));
  state.persistentSelection = c[5] ? &saved : nullptr;
  state.hasRemoteHandler = c[4];
  state.milliseconds = fixtureClock;
  state.restoreTicks = &last;
  Presonus::Mixer::NetworkSetupComponent target(state);
  RangeObserver observer;
  list->addObserver(&observer);
  int result = 0;
  Event event{};
  switch (c[0]) {
  case 1:
    target.onIdle();
    break;
  case 2:
    result = target.sendEvent(event);
    break;
  case 3:
    target.onNetworkItemAdded(services.item(static_cast<int>(c[2])));
    break;
  case 4:
    target.selectMixer(services.item(static_cast<int>(c[2])), c[16]);
    break;
  case 5:
    target.paramChanged(&changed, static_cast<int>(c[8]));
    break;
  case 6:
    result = target.getConnectedClient() ? 9 : 0;
    break;
  case 7:
    target.onNetworkShutdown();
    break;
  case 8:
    target.checkRestoreMixer();
    break;
  case 9:
    target.onNetworkItemRemoved(services.item(static_cast<int>(c[2])));
    break;
  case 10:
    target.syncListParam(0, state.items, state.selected);
    break;
  default:
    std::abort();
  }
  std::vector<int> items;
  for (int i = 0; i < state.items.count(); ++i)
    items.push_back(services.id(*state.items[i]));
  std::vector<std::string> strings;
  for (int i = 0; i < list->getStringCount(); ++i)
    strings.emplace_back(list->getStringAt(i));
  char nameText[256], savedText[256];
  name->toString(nameText, 256);
  saved.toString(savedText, 256);
  std::cout << "{\"trace\":" << arrayJSON(services.trace)
            << ",\"list\":" << arrayJSON(strings)
            << ",\"value\":" << static_cast<int>(list->getValue())
            << ",\"name\":" << quote(nameText) << ",\"connected\":"
            << static_cast<int>(parameters.getParameterByTag(3)->getValue())
            << ",\"saved\":" << quote(savedText)
            << ",\"ranges\":" << observer.ranges << ",\"selected\":"
            << (state.selected ? services.id(*state.selected) : 0)
            << ",\"items\":" << arrayJSON(items) << ",\"last\":" << last
            << ",\"result\":" << result << "}\n";
  list->removeObserver(&observer);
}
} // namespace
int main() {
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::array<std::int64_t, 17> c{};
    for (auto &v : c)
      if (!(in >> v))
        return 2;
    run(c);
  }
}

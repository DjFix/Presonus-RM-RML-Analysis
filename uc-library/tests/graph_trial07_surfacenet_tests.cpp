#include "presonus/surface/NetworkSetupComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
using namespace Core::Portable;
namespace {
std::string q(const std::string &s) {
  std::string r = "\"";
  for (char c : s) {
    if (c == '"' || c == '\\')
      r += '\\';
    r += c;
  }
  return r + '"';
}
template <class T> std::string arr(const T &xs) {
  std::string r = "[";
  for (const auto &x : xs) {
    if (r.size() > 1)
      r += ',';
    r += x;
  }
  return r + ']';
}
using Item = Presonus::UC::NetworkItem;
Item *item(int i) {
  return reinterpret_cast<Item *>(static_cast<uintptr_t>(i));
}
int id(const Item *p) {
  return static_cast<int>(reinterpret_cast<uintptr_t>(p));
}
struct TestComponent : Component {
  void add(Parameter *p) { paramList.add(p); }
};
struct Scenario;
ParamInfo *makeInfo(int tag, int type) {
  auto *p = new ParamInfo{};
  p->tag = tag;
  p->type = type;
  p->minValue = -100000;
  p->maxValue = 100000;
  std::strcpy(p->name, "fixture");
  return p;
}
struct List : ListParam {
  std::vector<std::string> &trace;
  int tag;
  int requested = 0;
  List(int t, std::vector<std::string> &tr)
      : ListParam(*makeInfo(t, ParamInfo::kInt), true), trace(tr), tag(t) {}
  void setValue(ParamValue v, bool edit = false) override {
    requested = static_cast<int>(v);
    trace.push_back("[\"setValue\"," + std::to_string(tag) + "," +
                    std::to_string(requested) + "," + std::to_string(edit) +
                    "]");
    ListParam::setValue(v, edit);
  }
};
struct Observer : IParamObserver {
  void *castTo(TypeID type) override {
    return type == IParamObserver::kTypeID ? this : nullptr;
  }
  std::vector<std::string> &trace;
  explicit Observer(std::vector<std::string> &t) : trace(t) {}
  void paramChanged(Parameter *p, int msg) override {
    if (msg == Parameter::kRangeChanged)
      trace.push_back("[\"rangeChanged\"," + std::to_string(p->getTag()) + "]");
  }
};
struct Text : StringParam {
  std::vector<std::string> &trace;
  explicit Text(std::vector<std::string> &tr)
      : StringParam(*makeInfo(29, ParamInfo::kString), true), trace(tr) {}
  void fromString(const char *text, bool edit = false) override {
    trace.push_back("[\"fromString\",29," + q(text) + "," +
                    std::to_string(edit) + "]");
    StringParam::fromString(text, edit);
  }
};
struct Model : ListViewModel {
  std::vector<std::string> &trace;
  explicit Model(std::vector<std::string> &t) : trace(t) {}
  void changed() override {
    trace.push_back("[\"modelChanged\"]");
    ListViewModel::changed();
  }
  std::string rows() {
    std::vector<std::string> out;
    for (int i = 0; i < items.count(); ++i)
      out.push_back(
          "[" + q(items[i]->getTitle().str()) + "," +
          std::to_string(id(static_cast<Item *>(items[i]->getUserData()))) +
          "]");
    return arr(out);
  }
};
struct Scenario : presonus::surface::SurfaceNetworkDependencies,
                  presonus::surface::SurfaceNetworkProvider {
  std::array<int, 25> v;
  mutable std::vector<std::string> trace;
  std::array<std::string, 8> mapping;
  void event(const std::string &name,
             std::initializer_list<int> args = {}) const {
    std::string s = "[" + q(name);
    for (int n : args)
      s += ',' + std::to_string(n);
    trace.push_back(s + "]");
  }
  int kind(const Item &p) const override {
    int i = id(&p);
    return i == v[6] ? v[7] : i < 3 ? 0 : 1;
  }
  Item *associatedItem(const Item &) const override {
    return v[14] ? item(v[6]) : nullptr;
  }
  void title(const Item &p, Core::CStringBuffer<128> &out) const override {
    int i = id(&p);
    event("title", {i});
    out = ("T" + std::to_string(i) + std::string(v[23], 'x')).c_str();
  }
  const char *host(const Item &) const override { return "10.0.0.1"; }
  int mappingCount() const override {
    event("mappingCount");
    return v[8];
  }
  const char *mappingName(int i) const override {
    event("mappingName", {i});
    return mapping[i].c_str();
  }
  int targetType() const override {
    event("targetType");
    return v[10];
  }
  bool stored(const char *key, Item *p) const override {
    trace.push_back("[\"stored\"," + q(key) + "," + std::to_string(id(p)) +
                    "]");
    return v[13];
  }
  void acquire(Item *p) override { event("acquire", {id(p)}); }
  void release(Item *p, bool flag) override { event("release", {id(p), flag}); }
  void *component(Item *p) override {
    event("component", {id(p)});
    return v[15] ? reinterpret_cast<void *>(1) : nullptr;
  }
  void *mixerCast(void *) override {
    return v[16] ? reinterpret_cast<void *>(1) : nullptr;
  }
  void *dawCast(void *) override {
    return v[16] ? reinterpret_cast<void *>(1) : nullptr;
  }
  void setMixer(void *p) override { event("setMixer", {p != nullptr}); }
  void setDAW(void *p) override { event("setDAW", {p != nullptr}); }
  void setTransport(void *p) override { event("setTransport", {p != nullptr}); }
  void itemInfo(int t, Item *p) override { event("itemInfo", {t, id(p)}); }
  void storeSelected(const char *key, Item *p, int flags) override {
    trace.push_back("[\"storeSelected\"," + q(key) + "," +
                    std::to_string(id(p)) + "," + std::to_string(flags) + "]");
  }
  void setNetworkRoot(Component *p) override {
    event("setNetworkRoot", {p != nullptr && v[16] != 0});
  }
  void selectModelItem(Item *p) override { event("selectModelItem", {id(p)}); }
  int wiredAssignMode() const override { return v[21]; }
  void configureNetwork(const char *p) override {
    trace.push_back("[\"configureNetwork\"," + q(p) + "]");
  }
  void resumeAdaptors() override { event("resumeAdaptors"); }
  void enableNetwork(bool b) override { event("enableNetwork", {b}); }
  void setupLocalIP() override { event("setupLocalIP"); }
  int localAddresses(Core::Sockets::IPAddress *p, int) const override {
    event("localAddresses");
    for (int i = 0; i < v[11]; ++i)
      p[i].setIP(v[12], 0, 0, 1);
    return v[11];
  }
  bool parseAddress(Core::Sockets::SocketAddress &,
                    const char *text) const override {
    trace.push_back("[\"parseAddress\"," + q(text) + "]");
    return v[22];
  }
  explicit Scenario(char **args) {
    for (int i = 0; i < 25; ++i)
      v[i] = std::stoi(args[i]);
    for (int i = 0; i < 8; ++i)
      mapping[i] = "Map" + std::to_string(i);
  }
};
std::string ids(const Core::Vector<Item *> &xs) {
  std::vector<std::string> out;
  for (int i = 0; i < xs.count(); ++i)
    out.push_back(std::to_string(id(xs[i])));
  return arr(out);
}
std::string param(const List &p) {
  std::vector<std::string> out;
  for (int i = 0; i < p.getStringCount(); ++i)
    out.push_back(q(p.getStringAt(i)));
  return "{\"strings\":" + arr(out) +
         ",\"requested_value\":" + std::to_string(p.requested) + "}";
}
} // namespace
int main(int argc, char **argv) {
  if (argc != 26)
    return 2;
  Scenario s(argv + 1);
  TestComponent params;
  auto *p0 = new List(0, s.trace);
  auto *p7 = new List(7, s.trace);
  auto *p29 = new Text(s.trace);
  params.add(p0);
  params.add(p7);
  params.add(p29);
  Observer observer(s.trace);
  p0->addObserver(&observer);
  p7->addObserver(&observer);
  Presonus::DelayTimer timer(0.001f);
  presonus::timing::DelayTimerAccess::set(timer, {0, 1, s.v[20], 0, false});
  Model model(s.trace);
  presonus::surface::SurfaceNetworkState st{params, s, s, timer};
  for (int i = 1; i <= s.v[2]; ++i)
    st.mixers.add(item(i));
  for (int i = 3; i < 3 + s.v[3]; ++i)
    st.daws.add(item(i));
  st.selectedMixer = item(s.v[4]);
  st.selectedDAW = item(s.v[5]);
  st.selectedMidiMapping = s.v[9];
  st.model = s.v[24] ? &model : nullptr;
  st.adaptorConfigPending = s.v[18];
  Presonus::Surface::NetworkSetupComponent target(st);
  switch (s.v[0]) {
  case 1:
    target.syncListParam(s.v[1], s.v[1] == 7 ? st.daws : st.mixers,
                         s.v[1] == 7 ? st.selectedDAW : st.selectedMixer);
    break;
  case 2:
    target.onNetworkItemAdded(item(s.v[6]));
    break;
  case 3:
    target.selectMixer(item(s.v[6]), s.v[17]);
    break;
  case 4:
    target.selectDAW(item(s.v[6]), s.v[17]);
    break;
  case 5:
    target.setupListModel();
    break;
  case 6: {
    alignas(16) std::array<unsigned char, 16> opaque{};
    target.adaptorConfigChanged(
        *reinterpret_cast<const Presonus::WIFIManager *>(opaque.data()));
    break;
  }
  case 7:
    target.onIdle();
    break;
  case 8:
    target.onNetworkShutdown();
    break;
  case 9:
    target.onNetworkItemRemoved(item(s.v[6]));
    break;
  case 10:
    target.setupNetworkInfo();
    break;
  }
  char text[128]{};
  p29->toString(text, 128);
  int reset = s.v[0] == 7 && s.v[20] &&
              presonus::timing::DelayTimerAccess::get(timer).elapsed == 0;
  std::cout << "{\"trace\":" << arr(s.trace) << ",\"mixers\":" << ids(st.mixers)
            << ",\"daws\":" << ids(st.daws)
            << ",\"selectedMixer\":" << id(st.selectedMixer)
            << ",\"selectedDAW\":" << id(st.selectedDAW)
            << ",\"pending\":" << st.adaptorConfigPending
            << ",\"params\":{\"0\":" << param(*p0) << ",\"7\":" << param(*p7)
            << ",\"29\":{\"text\":" << q(text) << "}},\"rows\":" << model.rows()
            << ",\"timerReset\":" << reset << "}\n";
  p0->removeObserver(&observer);
  p7->removeObserver(&observer);
}

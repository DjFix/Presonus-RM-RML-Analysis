#include "presonus/surface/CapturePageComponent.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>
using namespace Core::Portable;
namespace {
std::vector<std::string> trace;
std::map<std::string, uint32_t> cfg;
uint32_t get(const std::string &key, uint32_t fallback = 1) {
  auto i = cfg.find(key);
  return i == cfg.end() ? fallback : i->second;
}
uint32_t bits(float value) {
  uint32_t n;
  std::memcpy(&n, &value, 4);
  return n;
}
float value(uint32_t n) {
  float f;
  std::memcpy(&f, &n, 4);
  return f;
}
void emit(const std::string &s) { trace.push_back(s); }
struct Numeric : NumericParam {
  int id;
  Numeric(const ParamInfo &info, int id, float initial)
      : NumericParam(info), id(id) {
    value = initial;
  }
  void setValue(float v, bool edit = false) override {
    emit("set\t" + std::to_string(id) + "\t" + std::to_string(bits(v)) + "\t" +
         std::to_string(edit));
    NumericParam::setValue(v, edit);
  }
};
struct Alias : AliasParam {
  using AliasParam::AliasParam;
  bool feedback() const { return (flags & kFeedback) != 0; }
};
struct Params : Component {
  void add(Parameter *p) { paramList.add(p); }
};
struct PageBindings : presonus::page::Bindings {
  const void *page = nullptr;
  void *castOwner(void *, int) const override {
    emit("screen");
    return get("screen") ? reinterpret_cast<void *>(1) : nullptr;
  }
  const void *currentPage(void *) const override {
    return get("showing") ? page : nullptr;
  }
  void stopTextInput(void *, bool) const override {}
  bool isEditingText(void *) const override { return false; }
};
struct App : presonus::capture::Bindings {
  mutable Core::Vector<void *> oldMembers, newMembers;
  Params &remote;
  App(Params &p) : remote(p) {}
  Core::Vector<void *> &
  observers(Presonus::DAWClientComponent *p) const override {
    return p == reinterpret_cast<Presonus::DAWClientComponent *>(2)
               ? oldMembers
               : newMembers;
  }
  Component *document(Presonus::DAWClientComponent *) const override {
    emit("document");
    return get("document") ? &remote : nullptr;
  }
  Component *recordDiskSpace(Presonus::DAWClientComponent *) const override {
    emit("server");
    return get("server") ? &remote : nullptr;
  }
  Component *session(Presonus::DAWClientComponent *) const override {
    emit("session");
    return get("session") ? &remote : nullptr;
  }
  Component *arrangement(Presonus::DAWClientComponent *) const override {
    return get("arrangement") ? &remote : nullptr;
  }
  void *timeInfo(Presonus::DAWClientComponent *) const override {
    emit("time");
    return get("time") ? reinterpret_cast<void *>(1) : nullptr;
  }
  void *castTimeInfo(void *p) const override {
    return get("cast") ? p : nullptr;
  }
  bool progress(Presonus::DAWClientComponent *) const override {
    emit("progress");
    return get("progress") != 0;
  }
  void setDelegate(Presonus::DAWClientComponent *p) const override {
    emit("delegate\t" + std::to_string(p != nullptr));
  }
  void baseOnShow(bool b) const override {
    emit("baseShow\t" + std::to_string(b));
  }
  void showStartPage(void *) const override { emit("closeModal"); }
  void *modalPage(void *) const override {
    emit("modal");
    return get("modal") ? reinterpret_cast<void *>(1) : nullptr;
  }
  void *castLoadPage(void *p) const override {
    return get("cast") ? p : nullptr;
  }
  void closeLoadPage(void *) const override { emit("close"); }
  void setTimeMode(void *, int n) const override {
    emit("timeMode\t" + std::to_string(n));
  }
  void setTimeFormat(void *, int n) const override {
    emit("timeFormat\t" + std::to_string(n));
  }
  void wheel(void *, int n) const override {
    emit("wheel\t" + std::to_string(static_cast<uint32_t>(n)));
  }
  void *createDocumentPage(Presonus::DAWClientComponent *, const char *a,
                           const char *b) const override {
    emit(std::string("construct\t") + a + "\t" + b);
    return reinterpret_cast<void *>(1);
  }
  void showModal(void *, void *) const override { emit("showModal"); }
  void command(Presonus::DAWClientComponent *, const char *a,
               const char *b) const override {
    emit(std::string("command\t") + a + "\t" + b);
  }
};
} // namespace
int main(int argc, char **argv) {
  if (argc < 3 || std::string(argv[1]) != "--case")
    return 2;
  int packet = std::stoi(argv[2]);
  for (int i = 3; i < argc; ++i) {
    std::string s = argv[i];
    auto p = s.find('=');
    cfg[s.substr(0, p)] = static_cast<uint32_t>(std::stoull(s.substr(p + 1)));
  }
  std::array<ParamInfo, 16> info{};
  Params remote, local;
  for (int i = 0; i < 16; ++i) {
    info[i].type = ParamInfo::kFloat;
    info[i].tag = i;
    info[i].minValue = -100.f;
    info[i].maxValue = 100.f;
    if (i != static_cast<int>(get("missing_remote", 0xffffffff)))
      remote.add(new Numeric(info[i], 100 + i,
                             value(get("remote_value", 0x3f800000))));
    if (i != static_cast<int>(get("missing_tag", 0xffffffff))) {
      if (packet == 2 && i >= 6 && get("cast"))
        local.add(new Alias(info[i]));
      else
        local.add(new Numeric(info[i], i, value(get("value", 0x3f800000))));
    }
  }
  App app(remote);
  PageBindings pageBindings;
  Presonus::PageComponent page(reinterpret_cast<void *>(1), pageBindings);
  pageBindings.page = &page;
  auto *daw = get("daw") ? reinterpret_cast<Presonus::DAWClientComponent *>(1)
                         : nullptr;
  auto *initial =
      packet == 2
          ? (get("old", 0) ? reinterpret_cast<Presonus::DAWClientComponent *>(2)
                           : nullptr)
          : daw;
  auto *sound = get("sound") ? remote.getParameterByTag(7) : nullptr;
  Presonus::Surface::CapturePageComponent capture(local, page, app, initial,
                                                  sound);
  for (auto key : {"old", "new"}) {
    auto &members = std::string(key) == "old" ? app.oldMembers : app.newMembers;
    auto count = get(std::string(key) + "_count", 0);
    auto mask = get(std::string(key) + "_mask", 0);
    for (uint32_t i = 0; i < count; ++i)
      members.add((mask & (1u << i)) ? static_cast<void *>(&capture)
                                     : reinterpret_cast<void *>(
                                           static_cast<uintptr_t>(16 + i)));
  }
  auto *p = get("same", 0)
                ? sound
                : local.getParameterByTag(static_cast<int>(get("tag", 0)));
  trace.clear();
  bool returned = false;
  switch (packet) {
  case 1:
    capture.onObjectChanged(
        static_cast<Presonus::IDAWComponentObserver::ObjectChangeMessage>(
            get("message", 2)));
    break;
  case 2:
    capture.setDAWComponent(daw);
    break;
  case 3:
    capture.syncSoundcheckParam();
    break;
  case 4:
    capture.onShow(get("show") != 0);
    break;
  case 5:
    capture.openSession();
    break;
  case 6:
    capture.syncInProgressParam();
    break;
  case 7:
    capture.setSoundcheckMode(p);
    break;
  case 8:
    returned = capture.loadSoundcheckSession();
    break;
  case 9:
    capture.onWheelInput(WheelEvent(static_cast<int>(get("wheel", 3))));
    break;
  case 10:
    capture.paramChanged(p, static_cast<int>(get("message", 2)));
    break;
  default:
    return 3;
  }
  for (const auto &line : trace)
    std::cout << "trace\t" << line << '\n';
  if (packet == 8)
    std::cout << "return\t" << returned << '\n';
  std::cout << "daw\t" << (capture.portableDAW() != nullptr) << "\nsound\t"
            << (capture.portableSoundcheck() != nullptr) << '\n';
  for (auto key : {"old", "new"}) {
    auto &members = std::string(key) == "old" ? app.oldMembers : app.newMembers;
    std::cout << key;
    for (int i = 0; i < members.count(); ++i)
      std::cout << '\t' << (members[i] == &capture);
    std::cout << '\n';
  }
  if (packet == 2)
    for (int i = 6; i < 14; ++i)
      if (auto *a = static_cast<Alias *>(
              AliasParam::cast(local.getParameterByTag(i)))) {
        auto *original = a->getOriginal();
        std::cout << "alias\t" << i << '\t'
                  << (original ? 100 + original->getTag() : -1) << '\n';
        if (i == 6)
          std::cout << "feedback\t6\t" << a->feedback() << '\n';
      }
  if (packet == 2 && capture.portableSoundcheck())
    capture.portableSoundcheck()->removeObserver(&capture);
  return 0;
}

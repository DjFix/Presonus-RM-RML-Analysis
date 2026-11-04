#include "presonus/mixer/MixerComponent.hpp"
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
using namespace Core::Portable;
using namespace Presonus::Mixer;
namespace {
std::vector<std::string> events;
template <class... T> void event(const char *name, T... values) {
  std::ostringstream s;
  s << "[\"" << name << "\"";
  ((s << ',' << values), ...);
  s << ']';
  events.push_back(s.str());
}
const ParamInfo info =
    PARAM_FLOAT(42, "test", -100, 100, 0, 1, nullptr, nullptr, 0, 0);
struct Param : NumericParam {
  float value{};
  int id{};
  explicit Param(int id = 0) : NumericParam(::info), id(id) {}
  float getValue() const override { return value; }
  void setValue(float v, bool edit) override {
    value = v;
    event("set", id, v, int(edit));
  }
};
struct ChannelServices : presonus::mixer::ChannelApplicationServices {
  bool isLinked(const ChannelComponent &) const override { return false; }
  void removeLink(ChannelComponent &) override {}
  ChannelComponent *linkablePair(ChannelComponent &) override {
    return nullptr;
  }
  void faderLocateDirty(ChannelComponent &) override {}
  void coefficientsChanged(ChannelComponent &, bool) override {}
};
struct LinkServices : Presonus::linkable_port::Boundary {
  Presonus::LinkableComponent *query(Presonus::LinkableComponent &,
                                     std::uint32_t) override {
    return nullptr;
  }
  void remove(Presonus::LinkableComponent &) override {}
  void set(Presonus::LinkableComponent &, Presonus::LinkableComponent &,
           bool) override {}
  void master(Presonus::LinkableComponent &,
              Presonus::LinkableComponent &) override {}
};
struct PresetServices : presonus::panel::PresetApplicationServices {
  using P = Presonus::Panel::PresetComponent;
  int selectedSlot(const P &) const override { return 0; }
  bool slotEmpty(const P &, unsigned) const override { return false; }
  void slotFileName(Core::CString256 &, const P &, unsigned) const override {}
  const char *presetFolder(const P &) const override { return ""; }
  void ensureNameManager() const override {}
  Presonus::Panel::PresetNameCache *lookupCache(const char *) const override {
    return nullptr;
  }
  bool hasSelectedSlotParameter(const P &) const override { return false; }
  void presetInfo(Core::CString64 &, Core::CString32 &, int,
                  const char *) const override {}
  const char *emptyNameMarker() const override { return ""; }
  void updateSelection(P &) override {}
  int recallAttributes(P &, Attributes &, bool) override { return 0; }
  void notifyDelegate(P::Delegate *, const P &, int, bool) const override {}
};
struct Services : presonus::mixer_component_port::MixerServices {
  std::vector<std::unique_ptr<ChannelComponent>> channels;
  std::vector<std::unique_ptr<Component>> components;
  std::vector<std::unique_ptr<Presonus::LinkableComponent>> links;
  Param source, destination{1}, select{2};
  bool excluded{};
  int type{}, attrs{};
  int index(const ChannelComponent *p) const {
    for (unsigned i = 0; i < channels.size(); ++i)
      if (channels[i].get() == p)
        return int(i);
    return -1;
  }
  void serverParamChanged(MixerComponent &, Parameter *, int flags) override {
    event("server", flags);
  }
  Component &parameterComponent(ChannelComponent &c) const override {
    int i = index(&c);
    event("lookup", i, 42);
    return *components[i];
  }
  Presonus::LinkableComponent *
  linkIdentity(ChannelComponent *c) const override {
    int i = index(c);
    return i < 0 ? nullptr : links[i].get();
  }
  const IStorageFilter *storageFilter(int selector, bool flag) override {
    event("filter", selector, int(flag));
    return nullptr;
  }
  void load(const InputStorage &storage) override {
    event("load", int(storage.getMode()[0]),
          storage.getAttributes().countAttributes(),
          int(storage.getFilter() == nullptr));
  }
  void save(OutputStorage &storage) override {
    event("save", int(storage.getMode()[0]),
          int(storage.getFilter() == nullptr));
    storage.getWriter().setValue("muted", Core::int64(1));
  }
  bool muteExcluded(const ChannelComponent &) const override {
    return excluded;
  }
  Parameter &muteSource(ChannelComponent &) override { return source; }
  Parameter &muteDestination(ChannelComponent &) override {
    return destination;
  }
  Parameter &selection(ChannelComponent &c) override {
    select.id = index(&c);
    return select;
  }
  const char *
  presetType(const Presonus::Panel::PresetComponent &) const override {
    event("presetType");
    return type == 0 ? nullptr : type == 1 ? "scene" : "other";
  }
  void command(const char *name, const char *key, int value) override {
    if (std::strcmp(name, "StoreAVBScene") || std::strcmp(key, "scene"))
      throw 1;
    event("command", value);
  }
};
struct Releasable : MixerComponent {
  using MixerComponent::MixerComponent;
  ~Releasable() override { event("delete-request"); }
};
} // namespace
int main(int argc, char **argv) {
  if (argc != 11)
    return 2;
  int i = std::stoi(argv[1]), count = std::stoi(argv[2]),
      match = std::stoi(argv[3]), attrs = std::stoi(argv[4]);
  Services svc;
  presonus::mixer_component_port::MixerState state;
  ChannelServices cs;
  LinkServices ls;
  presonus::mixer::ChannelState channelStates[8];
  Presonus::linkable_port::State linkStates[8];
  for (int j = 0; j < 8; ++j) {
    svc.channels.push_back(
        std::make_unique<ChannelComponent>(channelStates[j], cs));
    svc.components.push_back(std::make_unique<Component>());
    svc.components.back()->addParameters(&info, 1);
    svc.links.push_back(
        std::make_unique<Presonus::LinkableComponent>(linkStates[j], ls));
    if (j < count) {
      state.channels.add(svc.channels.back().get());
      state.equalizers.add(svc.links.back().get());
    }
  }
  state.muteEnabled = std::stoi(argv[5]);
  state.muteActive = std::stoi(argv[6]);
  svc.excluded = std::stoi(argv[7]);
  auto bits = std::uint32_t(std::stoul(argv[8]));
  std::memcpy(&svc.source.value, &bits, 4);
  svc.type = std::stoi(argv[9]);
  int extra = std::stoi(argv[10]);
  MixerComponent mixer(state, svc);
  Core::Portable::AttributeBufferAllocator allocator(4096);
  Attributes attributes(allocator);
  for (int j = 0; j < attrs; ++j) {
    std::string key = "a" + std::to_string(j);
    attributes.set(key.c_str(), j);
  }
  MixerComponentBase::Filter filter{7};
  int result = -1;
  Param absent;
  events.clear();
  switch (i) {
  case 1:
    mixer.paramChanged(&absent, extra);
    break;
  case 2:
    (new Releasable(state, svc))->release();
    break;
  case 3: {
    auto &p = match < 0 ? static_cast<Parameter &>(absent)
                        : *svc.components[match]->getParameterByTag(42);
    result = svc.index(mixer.findChannelOwningParameter(p));
    break;
  }
  case 4:
    mixer.restoreMutes(attributes, filter);
    break;
  case 5:
    mixer.doMute(svc.channels[0].get());
    break;
  case 6: {
    PresetServices ps;
    Presonus::Panel::PresetComponent preset(ps);
    mixer.presetStored(preset, extra);
    break;
  }
  case 7:
    mixer.onCascadeChannelSelect(17, -3);
    break;
  case 8: {
    auto *target = match < 0 ? svc.links[7].get() : svc.links[match].get();
    auto *p = mixer.getGeqLinkPartner(target);
    for (int j = 0; j < count; ++j)
      if (p == svc.links[j].get())
        result = j;
    break;
  }
  case 9: {
    auto *target = match < 0 ? svc.links[7].get() : svc.links[match].get();
    result = svc.index(mixer.getLinkPartner(target, state.channels));
    break;
  }
  case 10:
    mixer.rememberMutes(attributes, filter);
    break;
  default:
    return 3;
  }
  std::cout << "{\"result\":" << result << ",\"flags\":["
            << int(state.cascadeSelected) << ',' << int(state.cascadeDirty)
            << "],\"events\":[";
  for (unsigned j = 0; j < events.size(); ++j) {
    if (j)
      std::cout << ',';
    std::cout << events[j];
  }
  std::cout << "]}" << std::endl;
  if (i == 10 &&
      (attributes.countAttributes() != 1 || !attributes.contains("muted")))
    return 4;
}

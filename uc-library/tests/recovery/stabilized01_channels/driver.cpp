#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/SLChannel.hpp"
#include <cstdint>
#include <cstring>
#include <iostream>
#include <memory>
#include <vector>

using namespace Core::Portable;
// Test-only null-slot injection uses the actual CCL vector. Remove null slots
// before the real Component destructor; all actual child ownership stays CCL.
struct Group : Component {
  using Component::Component;
  void addNull() { children.add(nullptr); }
  ~Group() {
    while (children.remove(nullptr)) {
    }
  }
};
struct Value : NumericParam {
  using NumericParam::NumericParam;
  mutable int reads = 0;
  Core::Portable::ParamValue getValue() const override {
    ++reads;
    return NumericParam::getValue();
  }
};
const char *names[] = {"line", "return", "fxreturn", "talkback",
                       "aux",  "fxbus",  "sub",      "main",
                       "mono", "unused", "signalgen"};
int main() {
  int op;
  while (std::cin >> op) {
    if (op == 0) {
      Presonus::SLChannelBase base;
      ParamInfo info{};
      Value param(info);
      Presonus::SLChannel channel("c", &param), absent("a", nullptr);
      std::cout << (base.getSelectionParameter() == nullptr) << ' '
                << (channel.getSelectionParameter() == &param) << ' '
                << (absent.getSelectionParameter() == nullptr) << '\n';
    } else if (op == 1) {
      int type, present;
      std::cin >> type >> present;
      Component groups;
      if (present)
        for (int i = 0; i < 11; ++i)
          groups.addChild(new Component(names[i]));
      Presonus::MixerClientComponentBase mixer(groups);
      auto *found =
          mixer.getChannelGroup(static_cast<Presonus::ChannelType>(type));
      std::cout << (found ? found->getName().str() : "NULL") << '\n';
    } else if (op == 2) {
      std::string name;
      std::cin >> name;
      if (name == "<empty>")
        name.clear();
      Component group(name.c_str()), groups;
      Presonus::MixerClientComponentBase mixer(groups);
      std::cout << static_cast<int>(mixer.getChannelGroupType(group)) << '\n';
    } else if (op == 3) {
      int cached, total;
      std::cin >> cached >> total;
      Component groups;
      std::vector<std::unique_ptr<Value>> params;
      std::vector<Presonus::SLChannelBase *> ids(1, nullptr);
      Presonus::SLChannelBase cache;
      ParamInfo info{};
      info.type = ParamInfo::kFloat;
      info.minValue = -100.f;
      info.maxValue = 100.f;
      Group *byType[11]{};
      for (int i = 0; i < total; ++i) {
        int type, kind;
        std::uint32_t bits;
        std::cin >> type >> kind >> bits;
        if (!byType[type]) {
          byType[type] = new Group(names[type]);
          groups.addChild(byType[type]);
        }
        auto *group = byType[type];
        if (kind == 5) {
          ids.push_back(nullptr);
        } else if (kind == 0) {
          group->addNull();
          ids.push_back(nullptr);
        } else if (kind == 1) {
          group->addChild(new Component("plain"));
          ids.push_back(nullptr);
        } else if (kind == 2) {
          auto *c = new Presonus::SLChannelBase("base");
          group->addChild(c);
          ids.push_back(c);
        } else {
          Value *p = nullptr;
          if (kind == 4) {
            params.push_back(std::make_unique<Value>(info));
            p = params.back().get();
            float value;
            std::memcpy(&value, &bits, 4);
            p->setValueFast(value);
          }
          auto *c = new Presonus::SLChannel("channel", p);
          group->addChild(c);
          ids.push_back(c);
        }
      }
      Presonus::MixerClientComponentBase mixer(groups,
                                               cached ? &cache : nullptr);
      auto *result = mixer.getSelectedChannel();
      int id = cached ? -1 : 0;
      for (std::size_t i = 1; i < ids.size(); ++i)
        if (result && ids[i] == result)
          id = static_cast<int>(i);
      int reads = 0;
      for (auto &p : params)
        reads += p->reads;
      // Second call verifies the cached path and absence of extra parameter
      // reads.
      auto *again = mixer.getSelectedChannel();
      int readsAfter = 0;
      for (auto &p : params)
        readsAfter += p->reads;
      std::cout << id << ' ' << reads << ' ' << (again == result) << ' '
                << readsAfter << '\n';
    } else
      return 2;
  }
}

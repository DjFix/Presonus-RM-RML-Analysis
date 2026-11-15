#include "core/portable/coreparams.h"
#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
using namespace Core::Portable;
using Presonus::Mixer::ChannelComponent;
using Presonus::Mixer::MixerComponentBase;
float number(unsigned bits) {
  float f;
  std::memcpy(&f, &bits, 4);
  return f;
}
unsigned bits(float f) {
  unsigned u;
  std::memcpy(&u, &f, 4);
  return u;
}
struct Tree : Component {
  void attach(Parameter *p) { paramList.add(p); }
  void detach(Parameter *p) { paramList.remove(p); }
};
struct ActualChannel : ChannelComponent {
  explicit ActualChannel(presonus::mixer::ChannelState &s)
      : ChannelComponent(SourcePortConstruction{}, s) {}
  void attach(Parameter *p) { paramList.add(p); }
  void detach(Parameter *p) { paramList.remove(p); }
};
struct Capture : Component {
  std::vector<Parameter *> ids;
  std::vector<std::pair<int, int>> events;
  void paramChanged(Parameter *p, int msg) override {
    for (int i = 0; i < int(ids.size()); ++i)
      if (ids[i] == p) {
        events.emplace_back(i + 1, msg);
        return;
      }
    std::abort();
  }
};
int main(int argc, char **argv) {
  bool provider = argc > 1 && std::string(argv[1]) == "--provider";
  int a;
  unsigned b, c, d;
  int n;
  while (std::cin >> a >> b >> c >> d >> n) {
    std::vector<int> meta(n), present(n);
    std::vector<unsigned> initial(n);
    for (int i = 0; i < n; ++i)
      std::cin >> meta[i] >> present[i] >> initial[i];
    std::string token;
    std::cin >> token;
    const char *name =
        token == "-" ? nullptr : (token == "!" ? "" : token.c_str());
    Tree root;
    Capture observer;
    std::vector<ParamInfo> infos(n);
    std::vector<std::unique_ptr<NumericParam>> params(n);
    std::vector<presonus::mixer::ChannelState> states(n);
    std::vector<std::unique_ptr<ActualChannel>> channels;
    Core::Vector<ChannelComponent *> collection;
    std::vector<std::pair<ChannelComponent *, int>> classifications;
    for (int i = 0; i < n; ++i) {
      if (TASK_KIND == 4 || TASK_KIND == 5 || TASK_KIND == 6) {
        channels.push_back(std::make_unique<ActualChannel>(states[i]));
        collection.add(channels.back().get());
        classifications.emplace_back(channels.back().get(), meta[i]);
      }
      if (present[i]) {
        const ParamInfo pi =
            PARAM_FLOAT((TASK_KIND == 4) ? i + 1 : meta[i], "actual", -100, 100,
                        0, 0, nullptr, nullptr, 0, 0);
        infos[i] = pi;
        params[i] = std::make_unique<NumericParam>(infos[i]);
        params[i]->setValue(number(initial[i]), false);
        params[i]->setController(&observer);
        params[i]->setFeedbackNeeded(true);
        params[i]->addObserver(&observer);
        if (TASK_KIND == 5)
          channels[i]->attach(params[i].get());
        else
          root.attach(params[i].get());
        if (TASK_KIND == 4)
          states[i].solo = params[i].get();
      }
      observer.ids.push_back(params[i].get());
    }
    std::vector<std::unique_ptr<Component>> children;
    if (TASK_KIND == 1) {
      const char *names[] = {"alpha", "", "selch", "alpha"};
      for (unsigned i = 0; i < b; ++i) {
        auto ch = std::make_unique<Component>();
        ch->setName(names[i % 4]);
        root.addChild(ch.get());
        children.push_back(std::move(ch));
      }
    }
    Component special;
    auto childId = [&](Component *p) {
      if (p == &special)
        return 99;
      for (int i = 0; i < int(children.size()); ++i)
        if (children[i].get() == p)
          return i + 1;
      if (!p)
        return 0;
      std::abort();
      return -1;
    };
    auto paramId = [&](Parameter *p) {
      if (!p)
        return 0;
      for (int i = 0; i < n; ++i)
        if (params[i].get() == p)
          return i + 1;
      std::abort();
      return -1;
    };
    auto snapshot = [&]() {
      std::cout << "P " << n;
      for (int i = 0; i < n; ++i)
        std::cout << ' ' << (params[i] ? bits(params[i]->getValue()) : 0);
      std::cout << " E " << observer.events.size();
      for (auto [id, msg] : observer.events)
        std::cout << ' ' << id << ' ' << msg;
      std::cout << '\n' << std::flush;
    };
    if (provider) {
      std::cout << "READY " << collection.count() << '\n' << std::flush;
      std::string op;
      while (std::cin >> op) {
        if (op == "done")
          break;
        if (op == "cmp") {
          std::cout << std::strcmp(name, "selch") << '\n';
        } else if (op == "find") {
          std::cout << childId(root.Component::findChild(name)) << '\n';
        } else if (op == "lookup") {
          int receiver, tag;
          std::cin >> receiver >> tag;
          auto *p = receiver ? channels.at(receiver - 1)->getParameterByTag(tag)
                             : root.getParameterByTag(tag);
          std::cout << paramId(p) << '\n';
        } else if (op == "get") {
          int id;
          std::cin >> id;
          std::cout << bits(params.at(id - 1)->getValue()) << '\n';
        } else if (op == "set") {
          int id, edit;
          unsigned u;
          std::cin >> id >> u >> edit;
          params.at(id - 1)->setValue(number(u), edit);
          std::cout << "OK\n";
        } else if (op == "edit") {
          int id;
          std::cin >> id;
          params.at(id - 1)->performEdit();
          std::cout << "OK\n";
        } else if (op == "snapshot") {
          snapshot();
          continue;
        } else
          std::abort();
        std::cout << std::flush;
      }
    } else {
#ifndef PROVIDER_ONLY
      MixerComponentBase mixer;
      mixer.sceneChannels = &collection;
      mixer.channelIdentity = [&](ChannelComponent *p) {
        for (auto [key, value] : classifications)
          if (key == p)
            return std::pair<std::int32_t, std::int32_t>{value, 0};
        std::abort();
        return std::pair<std::int32_t, std::int32_t>{0, 0};
      };
      if (TASK_KIND == 1) {
        mixer.childLookupParameters = &root;
        mixer.selectedChildParameters = a ? &special : nullptr;
        std::cout << childId(mixer.findChild(name)) << '\n';
      }
      if (TASK_KIND == 2) {
        mixer.sceneSettings = a ? &root : nullptr;
        std::cout << mixer.isSubgroupMerge() << '\n';
      }
      if (TASK_KIND == 3) {
        mixer.digitalOutputParameters = &root;
        mixer.refreshDigitalOutputRoutes();
        snapshot();
      }
      if (TASK_KIND == 4)
        std::cout << mixer.countSolos(a) << '\n';
      if (TASK_KIND == 5) {
        mixer.setChannelParams(a, number(b));
        snapshot();
      }
      if (TASK_KIND == 6) {
        mixer.mixChannels = collection;
        mixer.tdmConfigWord = b;
        unsigned char byte = c;
        mixer.routeByteView = d ? &byte : nullptr;
        unsigned char first = 0xa5, second = 0x5a;
        unsigned count = 0xdeadbeef;
        mixer.getTDMRoutes(a, first, second, count);
        std::cout << unsigned(first) << ' ' << unsigned(second) << ' ' << count
                  << ' ' << mixer.mixChannels.count() << '\n';
      }
#else
      std::abort();
#endif
    }
    for (int i = 0; i < n; ++i)
      if (params[i]) {
        params[i]->removeObserver(&observer);
        params[i]->setController(nullptr);
        if (TASK_KIND == 5)
          channels[i]->detach(params[i].get());
        else
          root.detach(params[i].get());
      }
    for (auto &child : children)
      root.removeChild(child.get());
  }
}

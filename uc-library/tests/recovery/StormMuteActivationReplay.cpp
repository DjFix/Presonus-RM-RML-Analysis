#include "core/portable/corepersistence.h"
#include "presonus/FileMuteGroup.hpp"
#include "presonus/StormMuteGroupComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Core::Portable;
static void require(bool v) {
  if (!v)
    throw std::runtime_error("activation replay mismatch");
}
static const Presonus::FileMuteGroup *watched = nullptr;
static void *topAttributes = nullptr;
static int archiveCalls = 0;
static int cleanupCount = 0, cleanupMembers = -1;
extern "C" void realD1(void *) asm("__real__ZN4Core8Portable10AttributesD1Ev");
extern "C" void wrapD1(void *p) asm("__wrap__ZN4Core8Portable10AttributesD1Ev");
extern "C" void wrapD1(void *p) {
  if (watched && p == topAttributes) {
    ++cleanupCount;
    cleanupMembers = watched->portableMemberCount();
  }
  realD1(p);
}
extern "C" void realD2(void *) asm("__real__ZN4Core8Portable10AttributesD2Ev");
extern "C" void wrapD2(void *p) asm("__wrap__ZN4Core8Portable10AttributesD2Ev");
extern "C" void wrapD2(void *p) {
  if (watched && p == topAttributes) {
    ++cleanupCount;
    cleanupMembers = watched->portableMemberCount();
  }
  realD2(p);
}
extern "C" bool realArchive(
    Attributes &, const char *, Archiver::Format, FileStorageContext *, int,
    bool) asm("__real__ZN4Core8Portable12ArchiveUtils12loadFromFileERNS0_"
              "10AttributesEPKcNS0_8Archiver6FormatEPNS0_"
              "18FileStorageContextEib");
extern "C" bool wrapArchive(
    Attributes &, const char *, Archiver::Format, FileStorageContext *, int,
    bool) asm("__wrap__ZN4Core8Portable12ArchiveUtils12loadFromFileERNS0_"
              "10AttributesEPKcNS0_8Archiver6FormatEPNS0_"
              "18FileStorageContextEib");
extern "C" bool wrapArchive(Attributes &a, const char *file,
                            Archiver::Format format,
                            FileStorageContext *context, int flags,
                            bool inplace) {
  if (watched) {
    require(format == Archiver::kJSON && context == nullptr && flags == 0 &&
            !inplace);
    topAttributes = &a;
    ++archiveCalls;
  }
  return realArchive(a, file, format, context, flags, inplace);
}
struct Tree : Component {
  bool accept = true, throws = false;
  int calls = 0;
  const Presonus::FileMuteGroup *group = nullptr;
  bool load(const InputStorage &storage) override {
    ++calls;
    require(group->portableMemberCount() == 1);
    require(storage.getFilter() != nullptr &&
            storage.getParentAttributes() == nullptr);
    require(!storage.isCanceled());
    if (throws)
      throw std::runtime_error("tree failure");
    return accept && Component::load(storage);
  }
};
static const ParamInfo infos[] = {
    PARAM_FLOAT(0, "mute", 0, 1, 0, 1, nullptr, nullptr, 0, PARAM_STORABLE),
    PARAM_FLOAT(1, "gain", 0, 10, 0, 1, nullptr, nullptr, 0, PARAM_STORABLE)};
struct Trigger : NumericParam {
  Trigger() : NumericParam(infos[0]) {}
  int observers() const { return observerList.count(); }
};
struct Services : presonus::storm_mute_port::Services {
  void refreshSip() override {}
  void activate(unsigned) override {
    throw std::runtime_error("forbidden service activate");
  }
  Component *connectedClient() override { return nullptr; }
  void muteGroupStored(int) override {}
  bool load(presonus::storm_mute_port::Group &) override {
    throw std::runtime_error("forbidden service load");
  }
};
int providerCases(int argc, char **argv) {
  require(argc == 2);
  std::filesystem::path dir(argv[1]);
  std::filesystem::create_directories(dir);
  int passed = 0;
  for (int mode = 0; mode < 7; ++mode) {
    Tree tree;
    auto *input = new Component("input");
    tree.addChild(input);
    auto *a = new Component("a");
    auto *b = new Component("b");
    input->addChild(a);
    input->addChild(b);
    a->addParameters(infos, 2);
    b->addParameters(infos, 2);
    auto *ma = a->findParameter("mute");
    auto *mb = b->findParameter("mute");
    auto *gain = a->findParameter("gain");
    ma->setValue(0, false);
    mb->setValue(0, false);
    gain->setValue(7, false);
    Presonus::Mixer::MixerComponentBase mixer;
    mixer.saveServices.parameters = &tree;
    Trigger trigger;
    NumericParam groupStatus(infos[0]);
    groupStatus.setMax(2);
    presonus::mute_group_port::MixerData data;
    data.channels.add({"input", "a", ma});
    data.channels.add({"input", "b", mb});
    auto path = (dir / ("case" + std::to_string(mode) + ".json")).string();
    // Independent provider inputs. mode 0 is an absent path in a fresh
    // directory.
    if (mode != 0) {
      std::ofstream file(path);
      file << (mode == 1   ? "{broken"
               : mode == 2 ? "{}"
               : mode == 5 ? "{\"input\":{\"a\":{\"mute\":2.5,\"gain\":2},"
                             "\"b\":{\"mute\":2.5,\"gain\":3}}}"
                           : "{\"input\":{\"a\":{\"mute\":1,\"gain\":2},\"b\":{"
                             "\"mute\":1,\"gain\":3}}}");
    }
    {
      Presonus::FileMuteGroup group(FileName(path.c_str()), &trigger, mixer);
      tree.group = &group;
      group.portableState().status = &groupStatus;
      group.portableBindMixerData(data);
      require(trigger.observers() == 1);
      DefaultAllocatedAttributes seed;
      seed.makeAttributes("input")->makeAttributes("a")->set("mute", 1);
      group.cacheMutes(seed);
      require(group.portableMemberCount() == 1);
      tree.accept = mode != 3;
      tree.throws = mode == 6;
      cleanupCount = 0;
      archiveCalls = 0;
      topAttributes = nullptr;
      cleanupMembers = -1;
      watched = &group;
      bool thrown = false;
      try {
        Services services;
        presonus::storm_mute_port::State stormState(services);
        presonus::storm_mute_port::Group adapter(group);
        require(&adapter.state == &group.portableState());
        stormState.groups.add(&adapter);
        Presonus::StormMuteGroupComponent storm(stormState);
        storm.activate(0);
        if (!tree.throws) {
          require(adapter.implementation.portableMemberCount() ==
                  group.portableMemberCount());
          storm.refreshGroups();
          require(!adapter.implementation.groupDirty() || mode == 0 ||
                  mode == 1 || mode == 3);
        }
      } catch (const std::runtime_error &) {
        thrown = true;
      }
      watched = nullptr;
      require(thrown == (mode == 6));
      require(cleanupCount == 1 && archiveCalls == 1);
      require(tree.calls == (mode >= 2 ? 1 : 0));
      require(gain->getValue() == 7);
      int members = mode == 2 ? 0 : mode == 4 || mode == 5 ? 2 : 1;
      require(group.portableMemberCount() == members &&
              cleanupMembers == members);
      require(ma->getValue() == (mode == 4 || mode == 5 ? 1 : 0));
      require(mb->getValue() == (mode == 4 || mode == 5 ? 1 : 0));
      if (mode == 4 || mode == 5) {
        Services services;
        presonus::storm_mute_port::State ss(services);
        presonus::storm_mute_port::Group binding(group);
        ss.groups.add(&binding);
        Presonus::StormMuteGroupComponent storm(ss);
        require(binding.state.members.count() == 2);
        require(groupStatus.getValue() == 2 && groupStatus.getMax() == 2);
        require(!binding.implementation.groupDirty());
        storm.deactivate(0);
        require(group.portableMemberCount() == 0 &&
                binding.state.members.count() == 0);
        require(ma->getValue() == 0 && mb->getValue() == 0);
        require(groupStatus.getMax() == 0);
      }
      // Existing cache and observer/reactivation behavior remains live.
      group.portableSetReactivation(true);
      trigger.setValue(0, false);
      group.paramChanged(&trigger, 3);
      require(trigger.getValue() == 1 && !group.portableReactivation());
    }
    require(trigger.observers() == 0);
    ++passed;
  }
  return passed;
}

struct Activated : Presonus::MuteGroupBase {
  NumericParam &mute;
  int calls = 0;
  bool throws = false;
  Activated(presonus::mute_group_port::State &s, NumericParam &p)
      : MuteGroupBase(s), mute(p) {}
  void activate() override {
    ++calls;
    if (throws)
      throw std::runtime_error("activation boundary");
    state.members.empty();
    state.members.add(&mute);
    mute.setValue(1, false);
  }
};
int main(int argc, char **argv) {
  int passed = providerCases(argc, argv);
  Services services;
  for (int count : {0, 2})
    for (unsigned index : {0u, 1u, 2u, 0x7fffffffu, 0x80000000u, 0xffffffffu})
      for (bool sentinel : {false, true}) {
        NumericParam mute(infos[0]), status(infos[0]);
        status.setMax(1);
        presonus::mute_group_port::State a, b;
        a.status = &status;
        b.status = &status;
        Activated first(a, mute), last(b, mute);
        presonus::storm_mute_port::Group ga(first), gb(last);
        presonus::storm_mute_port::State ss(services);
        if (count) {
          ss.groups.add(&ga);
          ss.groups.add(&gb);
        }
        if (sentinel)
          ss.activationError = &last;
        Presonus::StormMuteGroupComponent storm(ss);
        storm.activate(index);
        std::cout << "dispatch " << index << " " << count << " " << sentinel
                  << " " << first.calls << " " << last.calls << " "
                  << status.getValue() << "\n";
        const bool valid = index < static_cast<unsigned>(count);
        require(first.calls == (valid && index == 0 ? 1 : 0));
        require(last.calls ==
                ((valid && index == 1) || (!valid && sentinel) ? 1 : 0));
        if (first.calls || last.calls)
          require(status.getValue() == 1);
        if (valid) {
          auto &selected = index == 0 ? first : last;
          require(!selected.groupDirty());
          storm.deactivate(index);
          require(selected.portableMemberCount() == 0 && mute.getValue() == 0);
        }
        ++passed;
      }
  {
    presonus::mute_group_port::State a;
    Presonus::MuteGroupBase base(a);
    base.activate();
    require(a.members.count() == 0);
    presonus::storm_mute_port::State ss(services);
    ss.groups.add(nullptr);
    Presonus::StormMuteGroupComponent storm(ss);
    storm.activate(0);
    ++passed;
  }
  {
    NumericParam mute(infos[0]), status(infos[0]);
    status.setMax(1);
    status.setValue(0, false);
    presonus::mute_group_port::State a;
    a.status = &status;
    Activated throwing(a, mute);
    throwing.throws = true;
    presonus::storm_mute_port::Group ga(throwing);
    presonus::storm_mute_port::State ss(services);
    ss.groups.add(&ga);
    Presonus::StormMuteGroupComponent storm(ss);
    bool caught = false;
    try {
      storm.activate(0);
    } catch (const std::runtime_error &) {
      caught = true;
    }
    require(caught && status.getValue() == 0 && throwing.calls == 1);
    ++passed;
  }
  std::cout << passed << " subtype/provider/bounds/exception cases passed\n";
}

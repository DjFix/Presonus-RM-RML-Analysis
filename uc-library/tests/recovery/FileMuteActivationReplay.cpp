#include "core/portable/corepersistence.h"
#include "presonus/FileMuteGroup.hpp"
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
int main(int argc, char **argv) {
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
        group.activate();
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
      // Existing cache and observer/reactivation behavior remains live.
      group.portableSetReactivation(true);
      trigger.setValue(0, false);
      group.paramChanged(&trigger, 3);
      require(trigger.getValue() == 1 && !group.portableReactivation());
    }
    require(trigger.observers() == 0);
    ++passed;
  }
  std::cout
      << passed
      << " actual CCL archive/tree/cache/cleanup/lifecycle cases passed\n";
}

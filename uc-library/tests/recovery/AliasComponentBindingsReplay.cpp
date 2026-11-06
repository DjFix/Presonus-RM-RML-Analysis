#include "presonus/AliasComponent.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <new>
#include <stdexcept>

// Test-only allocation fault injection. Core objects and methods remain the
// actual pinned provider; no production allocator replacement is introduced.
static int failAfter = -1;
static int liveAllocations = 0;
void *operator new(std::size_t size) {
  if (failAfter == 0) {
    failAfter = -1;
    throw std::bad_alloc();
  }
  if (failAfter > 0)
    --failAfter;
  if (void *p = std::malloc(size ? size : 1)) {
    ++liveAllocations;
    return p;
  }
  throw std::bad_alloc();
}
void *operator new[](std::size_t size) { return ::operator new(size); }
void operator delete[](void *p) noexcept { ::operator delete(p); }
void operator delete[](void *p, std::size_t) noexcept { ::operator delete(p); }
void operator delete(void *p) noexcept {
  if (p) {
    --liveAllocations;
    std::free(p);
  }
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }

using namespace Core::Portable;
struct Source : Component {
  using Component::Component;
  void add(int tag, const char *name, bool enabled) {
    ParamInfo info{};
    info.type = ParamInfo::kInt;
    info.tag = tag;
    info.maxValue = 100;
    std::strcpy(info.name, name);
    auto *p = new NumericParam(info, true);
    paramList.add(p);
    p->enable(enabled);
  }
};
struct Derived : Presonus::AliasComponent {
  using AliasComponent::AliasComponent;
};
struct Counter : ParamObserverBase {
  int changed = 0;
  int destroyed = 0;
  void paramChanged(Parameter *p, int msg) override {
    if (msg == Parameter::kChanged)
      ++changed;
    if (msg == Parameter::kDestroyed) {
      ++destroyed;
      p->removeObserver(this);
    }
  }
};
static void requireImpl(bool state, int line) {
  if (!state) {
    std::fprintf(stderr, "provider mismatch at line %d\n", line);
    throw std::runtime_error("provider replay mismatch");
  }
}
#define require(state) requireImpl((state), __LINE__)
static void supplementary() {
  Source source("source");
  source.add(7, "Level", true);
  source.add(-2, "Mute", false);
  {
    Presonus::AliasComponent warm("warm", source);
  }
  // Provider observer vectors intentionally retain capacity after detach.
  const int initial = liveAllocations;
  // Both the complete-object and base-object construction forms, plus every
  // throwing C++ allocation on their normal construction paths.
  for (bool derived : {false, true}) {
    int exceptions = 0;
    for (int n = 0; n < 16; ++n) {
      failAfter = n;
      try {
        if (derived) {
          Derived object("alias", source);
          failAfter = -1;
          require(object.countParameters() == 2);
        } else {
          Presonus::AliasComponent object("alias", source);
          failAfter = -1;
          require(object.countParameters() == 2);
        }
      } catch (const std::bad_alloc &) {
        failAfter = -1;
        ++exceptions;
      }
      if (liveAllocations != initial)
        std::fprintf(stderr,
                     "allocation delta n=%d derived=%d baseline=%d live=%d\n",
                     n, derived, initial, liveAllocations);
      require(liveAllocations == initial);
      // Exercise observers after cleanup; stale aliases would call freed state.
      source.getParameterAt(0)->setValue(n % 2);
    }
    require(exceptions >= 4);
  }
  // A throwing rebind keeps the borrowed source plus the completed prefix;
  // subsequent clear removes that prefix and detaches all provider observers.
  for (int n = 0; n < 16; ++n) {
    Presonus::AliasComponent partial("partial");
    failAfter = n;
    try {
      partial.setOriginal(&source);
    } catch (const std::bad_alloc &) {
    }
    failAfter = -1;
    require(partial.getOriginal() == &source);
    require(partial.countParameters() >= 0 && partial.countParameters() <= 2);
    partial.setOriginal(nullptr);
    require(partial.countParameters() == 0);
  }
  Source bounded("bounded");
  bounded.add(51, "1234567890123456789012345678901", false);
  {
    Presonus::AliasComponent named("name", bounded);
    require(std::strlen(named.getParameterAt(0)->getName()) == 31);
  }
  Presonus::AliasComponent alias("alias", source);
  auto *parameter = alias.getParameterAt(0);
  require(parameter->isOwnInfo() && parameter->getType() == ParamInfo::kAlias);
  require(parameter->getController() == &alias);
  require(parameter->getOriginal() == source.getParameterAt(0));
  Counter count;
  parameter->addObserver(&count);
  source.getParameterAt(0)->setValue(13);
  require(count.changed > 0 && parameter->getValue() == 13);
  const int oldChanges = count.changed;
  alias.setOriginal(&source);
  require(count.destroyed == 1 && count.changed == oldChanges + 1);
  source.getParameterAt(0)->setValue(14);
  alias.setOriginal(nullptr);
  source.getParameterAt(0)->setValue(15);
  require(source.countParameters() == 2);
  // A borrowed Parameter may die first: actual AliasParam observes destruction.
  auto ephemeral = std::make_unique<Source>("ephemeral");
  ephemeral->add(3, "Temporary", true);
  alias.setOriginal(ephemeral.get());
  ephemeral.reset();
  require(alias.getParameterAt(0)->getOriginal() == nullptr);
  alias.setOriginal(
      nullptr); // Does not dereference the dangling borrowed component.
  // Delegation through actual Component::paramChanged and actual provider
  // flags.
  auto *p = source.getParameterAt(0);
  p->setStorable(true);
  alias.setNeedsSave(false);
  alias.paramChanged(p, Parameter::kEdit);
  require(!alias.needsSave());
  alias.paramChanged(p, Parameter::kChanged);
  require(alias.needsSave());
  alias.setNeedsSave(false);
  p->setStorable(false);
  alias.paramChanged(p, Parameter::kChanged);
  require(!alias.needsSave());
  std::puts("{\"supplementary_passed\":true,\"allocation_failures\":true,"
            "\"observers\":true}");
}
int main(int argc, char **argv) {
  try {
    if (argc != 2)
      return 2;
    if (std::strcmp(argv[1], "supplementary") == 0) {
      supplementary();
      return 0;
    }
    const char *mode = argv[1];
    Source source("source"), replacement("new");
    source.add(7, "Level", true);
    source.add(-2, "Mute", false);
    replacement.add(31, "Other", false);
    std::unique_ptr<Presonus::AliasComponent> alias;
    if (!std::strcmp(mode, "C1"))
      alias = std::make_unique<Presonus::AliasComponent>("alias", source);
    else if (!std::strcmp(mode, "C2"))
      alias = std::make_unique<Derived>("alias", source);
    else {
      alias = std::make_unique<Presonus::AliasComponent>("alias");
      if (!std::strcmp(mode, "same") || !std::strcmp(mode, "replace") ||
          !std::strcmp(mode, "clear"))
        alias->setOriginal(&source);
      if (!std::strcmp(mode, "preserve")) {
        const ParamInfo info{ParamInfo::kAlias, 99, "Keep"};
        alias->addParameters(&info, 1, true);
      }
      if (!std::strcmp(mode, "empty")) {
        Source empty("empty");
        alias->setOriginal(&empty);
      } else if (!std::strcmp(mode, "null") || !std::strcmp(mode, "clear"))
        alias->setOriginal(nullptr);
      else if (!std::strcmp(mode, "replace"))
        alias->setOriginal(&replacement);
      else
        alias->setOriginal(&source);
    }
    require(alias->getOriginal() != nullptr || alias->countParameters() == 0);
    std::printf("{\"snapshot\":[");
    for (int i = 0; i < alias->countParameters(); ++i) {
      auto *p = alias->getParameterAt(i);
      std::printf("%s{\"tag\":%d,\"name\":\"%s\",\"enabled\":%s}", i ? "," : "",
                  p->getTag(), p->getName(), p->isEnabled() ? "true" : "false");
    }
    std::printf("],\"original_nonnull\":%s,\"getter_matches\":true}\n",
                alias->getOriginal() ? "true" : "false");
  } catch (const std::exception &e) {
    std::fprintf(stderr, "%s\n", e.what());
    return 1;
  }
}

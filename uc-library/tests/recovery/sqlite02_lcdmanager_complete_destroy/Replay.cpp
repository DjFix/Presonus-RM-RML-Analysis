#include "presonus/panel/LCDManager.hpp"

#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string_view>

using namespace Presonus::Panel;

namespace {
// Bind the real CCL slot without registering temporary objects for deletion
// at process exit.
class SingletonProbe : public LCDManager {
public:
  static void bind(LCDManager *manager) { theInstance = manager; }
  static LCDManager *current() { return theInstance; }
};

class Delegate final : public ILCDDelegate {
public:
  Book *getDefaultBook() const override {
    ++callbacks;
    return nullptr;
  }

  Core::Portable::Parameter *
  lookupElementParameter(const char *) const override {
    ++callbacks;
    return nullptr;
  }

  void doIdle() override { ++callbacks; }
  mutable int callbacks = 0;
};

void *watched = nullptr;
int deletes = 0;
LCDManager *instanceAtDelete = nullptr;
} // namespace

void operator delete(void *ptr) noexcept {
  if (ptr == watched) {
    ++deletes;
    instanceAtDelete = SingletonProbe::current();
  }
  std::free(ptr);
}

void operator delete(void *ptr, std::size_t) noexcept {
  ::operator delete(ptr);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string_view variant{argv[1]}, seed{argv[2]};
  if (variant != "D0" && variant != "D1")
    return 2;

  Delegate delegate;
  LCDManager independent{};
  alignas(LCDManager) unsigned char storage[sizeof(LCDManager)];
  LCDManager *manager =
      variant == "D0" ? new LCDManager{LCDManager::SourcePortConstruction{}}
                      : new (storage) LCDManager;
  manager->setDelegate(&delegate);
  watched = manager;
  LCDManager *expected = nullptr;
  if (seed == "receiver")
    SingletonProbe::bind(manager);
  else if (seed == "other") {
    expected = &independent;
    SingletonProbe::bind(expected);
  } else if (seed != "null")
    return 2;

  if (variant == "D0") {
    Core::Portable::Deletable *base = manager;
    delete base;
    assert(instanceAtDelete == expected);
  } else {
    manager->~LCDManager();
  }

  assert(SingletonProbe::current() == expected);
  SingletonProbe::bind(nullptr);
  std::cout << std::boolalpha
            << "{\"singleton_is_null\":" << (expected == nullptr)
            << ",\"deletes\":" << deletes
            << ",\"delegate_callbacks\":" << delegate.callbacks << "}\n";
}

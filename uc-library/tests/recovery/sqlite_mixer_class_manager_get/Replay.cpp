#include "presonus/MixerClassManager.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string_view>

namespace {
constexpr unsigned maxRecords = 7;
std::array<std::uintptr_t, maxRecords> records{};
std::uintptr_t backingArray = 0;
unsigned count = 0;
unsigned freed = 0;
bool comparing = false;
bool destroying = false;
bool backingArrayFreed = false;

void recordFree(void *pointer) {
  if (destroying) {
    assert(freed < count);
    assert(reinterpret_cast<std::uintptr_t>(pointer) == records[freed]);
    ++freed;
  }
}
} // namespace

extern "C" int __real_strcmp(const char *, const char *);
extern "C" int __wrap_strcmp(const char *lhs, const char *rhs) {
  if (comparing)
    std::printf("strcmp\t%s\t%s\n", lhs, rhs);
  return __real_strcmp(lhs, rhs);
}

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __real__ZdaPv(void *);
extern "C" void __wrap__ZdlPv(void *pointer) {
  recordFree(pointer);
  __real__ZdlPv(pointer);
}
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  recordFree(pointer);
  __real__ZdlPvm(pointer, size);
}
extern "C" void __wrap__ZdaPv(void *pointer) {
  if (destroying) {
    assert(freed == count && !backingArrayFreed);
    assert(reinterpret_cast<std::uintptr_t>(pointer) == backingArray);
    backingArrayFreed = true;
  }
  __real__ZdaPv(pointer);
}

namespace Presonus {
struct MixerClassManagerLifetimeProbe {
  static void run(std::string_view variant, const char *query, char **roster,
                  unsigned size) {
    assert(size <= maxRecords);
    std::array<std::array<char, 32>, maxRecords> buffers{};
    count = size;
    {
      MixerClassManager manager;
      assert(manager.classes_.getCapacity() == 0 &&
             manager.classes_.getDelta() == 5);
      for (unsigned index = 0; index < size; ++index) {
        const std::string_view name = roster[index];
        const char *borrowed = nullptr;
        if (name != "<null>") {
          assert(name.size() < buffers[index].size());
          name.copy(buffers[index].data(), name.size());
          borrowed = buffers[index].data();
        }
        auto *record = new MixerClassManager::MixerClass{borrowed, nullptr};
        assert(manager.classes_.add(record));
        records[index] = reinterpret_cast<std::uintptr_t>(record);
      }
      assert(manager.classes_.count() == static_cast<int>(size));
      if (size > 5)
        assert(manager.classes_.getCapacity() > 5);
      backingArray =
          reinterpret_cast<std::uintptr_t>(manager.classes_.getItems());

      comparing = true;
      if (variant == "get") {
        const auto *record = manager.getMixerClass(query);
        comparing = false;
        if (record) {
          unsigned index = 0;
          while (index < size && record != manager.classes_.at(index))
            ++index;
          assert(index < size && record->descriptor == nullptr);
          const std::string_view expected = roster[index];
          assert(record->name ==
                 (expected == "<null>" ? nullptr : buffers[index].data()));
          std::printf("result %u\n", index);
        } else {
          std::puts("result null");
        }
      } else {
        assert(variant == "is");
        const bool found = manager.isMixerClass(query);
        comparing = false;
        std::printf("result %d\n", found);
      }

      destroying = true;
    }
    destroying = false;
    assert(freed == size && backingArrayFreed == (size != 0));
    for (unsigned index = 0; index < size; ++index) {
      const std::string_view borrowed = roster[index];
      if (borrowed != "<null>")
        assert(std::string_view(buffers[index].data()) == borrowed);
    }
  }
};
} // namespace Presonus

int main(int argc, char **argv) {
  assert(argc >= 3);
  const char *query = std::string_view(argv[2]) == "<null>" ? nullptr : argv[2];
  Presonus::MixerClassManagerLifetimeProbe::run(argv[1], query, argv + 3,
                                                argc - 3);
}

#include "presonus/panel/PresetNameCache.hpp"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>

struct presonus::panel::PresetCacheAccess {
  static void capacity(Presonus::Panel::PresetNameCache &cache, int value) {
    cache.capacity = value;
  }
};
struct Sink : Presonus::Panel::PresetNameCache::ObserverSink {
  void changed(Presonus::Panel::PresetNameCache::Delegate *,
               Presonus::Panel::PresetNameCache &, int, const char *,
               const char *) override {
    std::abort();
  }
  void rebuilt(Presonus::Panel::PresetNameCache::Delegate *,
               Presonus::Panel::PresetNameCache &) override {
    std::abort();
  }
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  FILE *input = std::fopen(argv[1], "r");
  if (!input)
    return 3;
  unsigned word = 0;
  int cases = 0;
  Sink sink;
  Presonus::Panel::PresetNameCache cache("preset", Core::Portable::FileName(),
                                         0, 0, sink);
  while (std::fscanf(input, "%u", &word) == 1) {
    int signedValue;
    static_assert(sizeof(signedValue) == sizeof(word));
    std::memcpy(&signedValue, &word, sizeof(word));
    presonus::panel::PresetCacheAccess::capacity(cache, signedValue);
    if (static_cast<unsigned>(cache.getCapacity()) != word)
      return 4;
    ++cases;
  }
  std::fclose(input);
  if (cases != 10)
    return 5;
  for (int fill : {0, 85, 170, 255}) {
    alignas(Presonus::Panel::PresetNameCache::CacheInfo) unsigned char
        bytes[sizeof(Presonus::Panel::PresetNameCache::CacheInfo)];
    std::memset(bytes, fill, sizeof(bytes));
    auto *info = new (bytes) Presonus::Panel::PresetNameCache::CacheInfo;
    // Expected values are native-observed provider inputs plus pinned CCL's
    // real constructor output, independently checked below.
    Core::CString64 providerName("* Empty Location *");
    Core::CString32 providerCategory(nullptr);
    if (std::strcmp(info->name.str(), providerName.str()) ||
        std::strcmp(info->category.str(), providerCategory.str()) ||
        std::strcmp(info->name.str(), "* Empty Location *") ||
        !info->category.isEmpty())
      return 6;
    info->~CacheInfo();
  }
  std::printf("capacity %d native vectors; CacheInfo 4 placement lifetimes "
              "with actual pinned CCL providers\n",
              cases);
}

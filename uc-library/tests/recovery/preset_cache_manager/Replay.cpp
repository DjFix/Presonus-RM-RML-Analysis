#include "presonus/panel/PresetNameCache.hpp"
#include "presonus/panel/PresetNameManager.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>
static_assert(
    !std::is_copy_constructible_v<Presonus::Panel::PresetNameManager>);
static_assert(!std::is_copy_assignable_v<Presonus::Panel::PresetNameManager>);
using Cache = Presonus::Panel::PresetNameCache;
using Manager = Presonus::Panel::PresetNameManager;
namespace presonus::panel {
struct PresetCacheAccess {
  static std::string snapshot(Cache &c) {
    std::ostringstream o;
    o << c.type.str() << '|' << unsigned(static_cast<unsigned char>(c.typeName))
      << '|' << c.folder.str() << '|' << c.capacity << '|' << c.protectedSlots
      << '|' << c.dirty;
    for (int i = 0; i < c.entries.count(); ++i)
      o << '|' << c.entries[i].name.str() << ':' << c.entries[i].category.str();
    o << "|cats";
    for (int i = 0; i < c.categories.count(); ++i)
      o << '|' << c.categories[i].str();
    return o.str();
  }
  static void clean(Cache &c) { c.dirty = false; }
};
} // namespace presonus::panel
static std::string unhex(const std::string &s) {
  std::string r;
  if (s == "-")
    return r;
  for (size_t i = 0; i < s.size(); i += 2)
    r += char(std::stoi(s.substr(i, 2), nullptr, 16));
  return r;
}
static std::string hex(const char *p, size_t n) {
  const char *d = "0123456789abcdef";
  std::string r;
  for (size_t i = 0; i < n; ++i) {
    auto c = static_cast<unsigned char>(p[i]);
    r += d[c >> 4];
    r += d[c & 15];
  }
  return r.empty() ? "-" : r;
}
static void *watched = nullptr;
static unsigned watchedFrees = 0;
void operator delete(void *p) noexcept {
  if (p && p == watched)
    ++watchedFrees;
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
void operator delete[](void *p) noexcept { ::operator delete(p); }
void operator delete[](void *p, std::size_t) noexcept { ::operator delete(p); }
struct Info {
  Core::CString64 name;
  Core::CString32 category;
};
struct Vectors {
  Core::Vector<Info> info{0, 5};
  Core::Vector<Core::CString32> strings{0, 5};
  Core::Vector<void *> pointers{0, 5};
};
struct ManagerAccess : Manager {
  static void install(Manager *p) { theInstance = p; }
  static Manager *installed() { return theInstance; }
};
struct Sink : Cache::ObserverSink {
  int changes = 0, rebuiltCount = 0;
  void changed(Cache::Delegate *, Cache &, int, const char *,
               const char *) override {
    ++changes;
  }
  void rebuilt(Cache::Delegate *, Cache &) override { ++rebuiltCount; }
};
int main() {
  std::map<unsigned, std::unique_ptr<Vectors>> vectors;
  std::map<unsigned, void *> allocations;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string op, a, b;
    in >> op;
    if (op == "string") {
      int cap;
      in >> cap >> a;
      auto value = unhex(a);
      const char *p = a == "-" ? nullptr : value.c_str();
      if (cap == 64) {
        Core::CString64 s(p);
        std::cout << hex(s.str(), std::strlen(s.str()) + 1);
      } else {
        Core::CString32 s(p);
        std::cout << hex(s.str(), std::strlen(s.str()) + 1);
      }
    } else if (op == "file") {
      in >> a;
      auto value = unhex(a);
      Core::Portable::FileName p(a == "-" ? nullptr : value.c_str());
      std::cout << hex(p.str(), std::strlen(p.str()) + 1);
    } else if (op == "length") {
      in >> a;
      std::cout << std::strlen(unhex(a).c_str());
    } else if (op == "copy") {
      int n;
      in >> n >> a;
      std::vector<char> buffer(n);
      std::strncpy(buffer.data(), unhex(a).c_str(), n);
      std::cout << hex(buffer.data(), buffer.size());
    } else if (op == "state") {
      Cache c("state", 6);
      presonus::panel::PresetCacheAccess::clean(c);
      c.cachePreset("Saved nonempty preset", "Drums", 3);
      c.cachePreset("second", "Vocals", 8);
      c.cachePreset("rejected", "none", -1);
      c.cachePreset("rejected", "none", 10);
      Core::CString64 name("sentinel");
      Core::CString32 category("sentinel");
      bool valid = c.getPresetInfo(name, category, 3);
      std::cout << presonus::panel::PresetCacheAccess::snapshot(c) << '\t'
                << valid << ':' << name.str() << ':' << category.str();
      name = "sentinel";
      category = "sentinel";
      valid = c.getPresetInfo(name, category, 10);
      std::cout << '\t' << valid << ':' << name.str() << ':' << category.str();
    } else if (op == "compare") {
      in >> a >> b;
      std::cout << std::strcmp(unhex(a).c_str(), unhex(b).c_str());
    } else if (op == "resize") {
      unsigned id;
      int stride, size;
      in >> id >> stride >> size;
      auto &v = vectors[id];
      if (!v)
        v = std::make_unique<Vectors>();
      bool ok;
      int capacity;
      if (stride == 96) {
        ok = v->info.resize(size);
        capacity = v->info.getCapacity();
      } else if (stride == 32) {
        ok = v->strings.resize(size);
        capacity = v->strings.getCapacity();
      } else {
        ok = v->pointers.resize(size);
        capacity = v->pointers.getCapacity();
      }
      std::cout << ok << ' ' << capacity;
    } else if (op == "drop") {
      unsigned id;
      int stride;
      in >> id >> stride;
      auto it = vectors.find(id);
      if (it == vectors.end())
        return 21;
      auto &v = *it->second;
      watched = stride == 96   ? static_cast<void *>(v.info.getItems())
                : stride == 32 ? static_cast<void *>(v.strings.getItems())
                               : static_cast<void *>(v.pointers.getItems());
      auto before = watchedFrees;
      bool allocated = watched;
      vectors.erase(it);
      watched = nullptr;
      std::cout << allocated << ' ' << watchedFrees - before;
    } else if (op == "alloc") {
      unsigned id, size;
      in >> id >> size;
      if (allocations.count(id))
        return 22;
      allocations[id] = ::operator new(size);
      std::cout << allocations.size();
    } else if (op == "free") {
      unsigned id;
      in >> id;
      auto it = allocations.find(id);
      if (it == allocations.end())
        return 23;
      watched = it->second;
      auto before = watchedFrees;
      ::operator delete(it->second);
      watched = nullptr;
      allocations.erase(it);
      std::cout << watchedFrees - before << ' ' << allocations.size();
    } else if (op == "cache") {
      int slots;
      in >> slots >> a;
      Cache c(unhex(a).c_str(), slots);
      std::cout << presonus::panel::PresetCacheAccess::snapshot(c);
    } else if (op == "default") {
      Cache::CacheInfo info;
      std::cout << info.name.str() << ':' << info.category.str();
    } else if (op == "empty") {
      in >> a;
      Cache::CacheInfo info;
      info.name = unhex(a).c_str();
      info.category = "nonempty category";
      std::cout << info.isEmpty();
    } else if (op == "manager") {
      int count;
      in >> count;
      Manager m;
      const char *cats[] = {"Vocals", "Drums", "", "Vocals",
                            "012345678901234567890123456789012345"};
      for (int i = 0; i < count; ++i) {
        std::string type = "type" + std::to_string(i);
        std::string folder = "/tmp/source-port-presets/" + std::to_string(i);
        m.registerPresetType(type.c_str(), char(65 + i), folder.c_str(), i % 9,
                             i % 4, cats, i % 6);
      }
      m.registerPresetType("type0", '!', "/duplicate", 77, 77, nullptr, 0);
      for (int i = 0; i < m.countCaches(); ++i) {
        if (i)
          std::cout << '\t';
        std::cout << presonus::panel::PresetCacheAccess::snapshot(
            *m.getCache(i));
      }
      std::cout << '\t'
                << unsigned(static_cast<unsigned char>(
                       m.getPresetTypeName("missing")))
                << ':'
                << unsigned(
                       static_cast<unsigned char>(m.getPresetTypeName("type0")))
                << ':' << m.sourcePortCacheCapacity();
    } else if (op == "regression") {
      Sink sink;
      auto cache = std::make_unique<Cache>(
          "borrowed", Core::Portable::FileName("/tmp/absent-preset-replay"), 3,
          1, sink);
      auto *borrowed = cache.get();
      {
        Manager m;
        m.sourcePortAddCache(borrowed);
        m.sourcePortAddCache(nullptr);
        m.registerPresetType("owned", 'O', "/tmp/absent-preset-replay", 6, 2,
                             nullptr, 0);
        auto *owned = m.lookupCache("owned");
        presonus::panel::PresetCacheAccess::clean(*owned);
        owned->cachePreset("Real name", "Real category", 3);
        Core::CString64 n;
        Core::CString32 c;
        if (!owned->getPresetInfo(n, c, 3) || n != "Real name" ||
            c != "Real category")
          return 30;
        if (m.getPresetTypeName("owned") != 'O' ||
            m.getPresetTypeName("absent") != '?')
          return 31;
      }
      presonus::panel::PresetCacheAccess::clean(*borrowed);
      borrowed->addObserver(reinterpret_cast<Cache::Delegate *>(1));
      borrowed->cachePreset("borrowed remains alive", "category", 2);
      if (sink.changes != 1)
        return 32;
      watched = borrowed;
      auto before = watchedFrees;
      cache.reset();
      watched = nullptr;
      if (watchedFrees != before + 1)
        return 33;
      Cache *raw = new Cache("deleting", 3);
      watched = raw;
      before = watchedFrees;
      delete raw;
      watched = nullptr;
      if (watchedFrees != before + 1)
        return 34;
      auto *manager = new Manager;
      ManagerAccess::install(manager);
      manager->registerPresetType("delete-owned", 'D', "", 1, 0, nullptr, 0);
      watched = manager->getCache(0);
      before = watchedFrees;
      delete manager;
      watched = nullptr;
      if (watchedFrees != before + 1 || ManagerAccess::installed())
        return 35;
      Manager other;
      ManagerAccess::install(&other);
      {
        Manager unrelated;
      }
      if (ManagerAccess::installed() != &other)
        return 36;
      ManagerAccess::install(nullptr);
      std::cout << "borrowed-alive owned-freed cache-freed real-nonempty-state";
    } else if (op == "quit") {
      std::cout << vectors.size() << ' ' << allocations.size() << std::endl;
      return vectors.empty() && allocations.empty() ? 0 : 24;
    } else
      return 25;
    std::cout << std::endl;
  }
}

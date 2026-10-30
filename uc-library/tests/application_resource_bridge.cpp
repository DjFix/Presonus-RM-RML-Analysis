#include "presonus/application/ResourceLibrary.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace presonus::application {
struct ResourceAccess {
  static Core::Vector<Presonus::FirmwareBundle *> &
  items(Presonus::ResourceLibrary &library) {
    return library.bundles_;
  }
  static void set(Presonus::FirmwareBundle &bundle, const char *name,
                  unsigned version, const unsigned char *image, int size,
                  bool compressed) {
    bundle.name_ = name;
    bundle.version_ = version;
    bundle.image_ = image;
    bundle.image_size_ = size;
    bundle.compressed_ = compressed;
  }
  static std::string name(const Presonus::FirmwareBundle &b) {
    return b.name_.str();
  }
  static unsigned version(const Presonus::FirmwareBundle &b) {
    return b.version_;
  }
  static const unsigned char *image(const Presonus::FirmwareBundle &b) {
    return b.image_;
  }
  static int size(const Presonus::FirmwareBundle &b) { return b.image_size_; }
  static bool compressed(const Presonus::FirmwareBundle &b) {
    return b.compressed_;
  }
};
} // namespace presonus::application
namespace {
using Bundle = Presonus::FirmwareBundle;
using Library = Presonus::ResourceLibrary;
using Access = presonus::application::ResourceAccess;
void require(bool value) {
  if (!value)
    std::abort();
}
bool observing = false;
std::unordered_map<const void *, unsigned> managed;
std::unordered_map<unsigned, Bundle *> bundles;
std::unordered_map<const void *, bool> arrays;
std::vector<std::string> events;
std::array<unsigned char, 256> image;
unsigned nextId = 1;
std::string hex(const std::string &value) {
  constexpr char digits[] = "0123456789abcdef";
  std::string out;
  for (unsigned char byte : value) {
    out += digits[byte >> 4];
    out += digits[byte & 15];
  }
  return out.empty() ? "-" : out;
}
std::string unhex(const std::string &value) {
  if (value == "-" || value == "NULL")
    return {};
  require(value.size() % 2 == 0);
  std::string out;
  for (std::size_t i = 0; i < value.size(); i += 2)
    out += static_cast<char>(std::stoul(value.substr(i, 2), nullptr, 16));
  return out;
}
unsigned id(Bundle *bundle) {
  if (!bundle)
    return 0;
  const auto found = managed.find(bundle);
  require(found != managed.end() && found->second != 0);
  return found->second;
}
unsigned track(Bundle *bundle) {
  const bool previous = observing;
  observing = false;
  const unsigned value = nextId++;
  managed[bundle] = value;
  bundles[value] = bundle;
  observing = previous;
  return value;
}
void trackArray(Core::Vector<Bundle *> &items) {
  const bool previous = observing;
  observing = false;
  if (items.getItems())
    arrays[items.getItems()] = true;
  observing = previous;
}
void deleted(void *pointer, bool array) {
  if (!observing)
    return;
  if (array) {
    const auto found = arrays.find(pointer);
    if (found != arrays.end() && found->second) {
      found->second = false;
      observing = false;
      events.push_back("array");
      observing = true;
    }
  } else {
    const auto found = managed.find(pointer);
    if (found != managed.end() && found->second) {
      const unsigned value = found->second;
      found->second = 0;
      observing = false;
      events.push_back("bundle:" + std::to_string(value));
      observing = true;
    }
  }
}
void info(Core::Vector<Bundle *> &items) {
  std::cout << items.count() << ' ' << items.getCapacity() << ' '
            << items.getDelta();
  for (int index = 0; index < items.count(); ++index)
    std::cout << ' ' << id(items.at(index));
  std::cout << '\n';
}
const unsigned char *imageFor(unsigned token) {
  require(token <= image.size());
  return token ? image.data() + token - 1 : nullptr;
}
} // namespace
extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __real__ZdlPvm(void *, std::size_t) noexcept;
extern "C" void __real__ZdaPv(void *) noexcept;
extern "C" void __real__ZdaPvm(void *, std::size_t) noexcept;
extern "C" void __wrap__ZdlPv(void *p) noexcept {
  deleted(p, false);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) noexcept {
  deleted(p, false);
  __real__ZdlPvm(p, n);
}
extern "C" void __wrap__ZdaPv(void *p) noexcept {
  deleted(p, true);
  __real__ZdaPv(p);
}
extern "C" void __wrap__ZdaPvm(void *p, std::size_t n) noexcept {
  deleted(p, true);
  __real__ZdaPvm(p, n);
}
extern "C" void nativeC1(void *) asm("_ZN8Presonus15ResourceLibraryC1Ev");
extern "C" void nativeC2(void *) asm("_ZN8Presonus15ResourceLibraryC2Ev");
extern "C" void nativeD1(void *) asm("_ZN8Presonus15ResourceLibraryD1Ev");
extern "C" void nativeD2(void *) asm("_ZN8Presonus15ResourceLibraryD2Ev");

int main() {
  std::atexit([] { observing = false; });
  observing = true;
  std::unique_ptr<Core::Vector<Bundle *>> peer;
  Library *library = nullptr;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string op, arg;
    in >> op;
    if (op == "reset") {
      require(!peer && !library);
      for (const auto &entry : managed)
        require(entry.second == 0);
      observing = false;
      managed.clear();
      bundles.clear();
      arrays.clear();
      events.clear();
      nextId = 1;
      observing = true;
      std::cout << "OK\n";
    } else if (op == "peer_new") {
      require(!peer);
      peer = std::make_unique<Core::Vector<Bundle *>>(0, 5);
      std::cout << peer->resize(0) << '\n';
    } else if (op == "peer_resize") {
      int capacity;
      in >> capacity;
      require(static_cast<bool>(peer));
      const bool result = peer->resize(capacity);
      trackArray(*peer);
      std::cout << result << '\n';
    } else if (op == "peer_set") {
      require(static_cast<bool>(peer));
      peer->setCount(0);
      unsigned value;
      while (in >> value)
        require(peer->add(value ? bundles.at(value) : nullptr));
      trackArray(*peer);
      std::cout << "OK\n";
    } else if (op == "peer_info") {
      require(static_cast<bool>(peer));
      info(*peer);
    } else if (op == "peer_destroy") {
      require(static_cast<bool>(peer));
      peer.reset();
      std::cout << "OK\n";
    } else if (op == "bundle_new") {
      std::cout << track(new Bundle) << '\n';
    } else if (op == "bundle_set") {
      unsigned value, version, token, compressed;
      int size;
      in >> value >> arg >> version >> token >> size >> compressed;
      require(compressed <= 1);
      const auto name = unhex(arg);
      Access::set(*bundles.at(value), arg == "NULL" ? nullptr : name.c_str(),
                  version, imageFor(token), size, compressed != 0);
      std::cout << "OK\n";
    } else if (op == "bundle_info") {
      unsigned value;
      in >> value;
      auto &b = *bundles.at(value);
      const auto *data = Access::image(b);
      const unsigned token =
          data ? static_cast<unsigned>(data - image.data()) + 1 : 0;
      std::cout << hex(Access::name(b)) << ' ' << Access::version(b) << ' '
                << token << ' ' << Access::size(b) << ' '
                << Access::compressed(b) << '\n';
    } else if (op == "bundle_delete") {
      unsigned value;
      in >> value;
      ::operator delete(value ? static_cast<void *>(bundles.at(value))
                              : nullptr);
      std::cout << "OK\n";
    } else if (op == "native_new") {
      in >> arg;
      require(!library && (arg == "C1" || arg == "C2"));
      library = static_cast<Library *>(::operator new(sizeof(Library)));
      (arg == "C1" ? nativeC1 : nativeC2)(library);
      std::cout << "OK\n";
    } else if (op == "native_add_raw") {
      unsigned version, token, compressed;
      int size;
      in >> arg >> version >> token >> size >> compressed;
      require(library && compressed <= 1);
      const auto name = unhex(arg);
      auto &items = Access::items(*library);
      const int before = items.count();
      library->addFirmware(arg == "NULL" ? nullptr : name.c_str(), version,
                           imageFor(token), size, compressed != 0);
      require(items.count() == before + 1);
      const unsigned value = track(items.at(before));
      trackArray(items);
      std::cout << value << '\n';
    } else if (op == "native_add") {
      unsigned value;
      in >> value;
      require(library);
      library->addFirmware(value ? bundles.at(value) : nullptr);
      trackArray(Access::items(*library));
      std::cout << "OK\n";
    } else if (op == "native_get" || op == "native_version") {
      in >> arg;
      require(library);
      const auto name = unhex(arg);
      const char *query = arg == "NULL" ? nullptr : name.c_str();
      if (op == "native_get")
        std::cout << id(library->get(query)) << '\n';
      else
        std::cout << library->getRequiredVersion(query) << '\n';
    } else if (op == "native_info") {
      require(library);
      info(Access::items(*library));
    } else if (op == "native_destroy") {
      in >> arg;
      require(library && (arg == "D1" || arg == "D2"));
      (arg == "D1" ? nativeD1 : nativeD2)(library);
      ::operator delete(library);
      library = nullptr;
      std::cout << "OK\n";
    } else if (op == "trace") {
      std::cout << events.size();
      for (const auto &event : events)
        std::cout << ' ' << hex(event);
      std::cout << '\n';
    } else if (op == "quit") {
      require(!peer && !library);
      std::cout << "OK\n" << std::flush;
      return 0;
    } else
      return 2;
    std::cout << std::flush;
  }
  return 3;
}

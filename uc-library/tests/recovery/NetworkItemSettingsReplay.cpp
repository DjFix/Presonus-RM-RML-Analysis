#include "core/portable/corepersistence.h"
#include "presonus/surface/NetworkSetupComponent.hpp"
#include "presonus/uc/NetworkItem.hpp"
#include <cstring>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
using namespace Core::Portable;
namespace {
struct Dependencies : presonus::surface::SurfaceNetworkDependencies {
  int mappingCount() const override { throw std::logic_error("unused"); }
  const char *mappingName(int) const override {
    throw std::logic_error("unused");
  }
  int kind(const Presonus::UC::NetworkItem &) const override {
    throw std::logic_error("unused");
  }
  Presonus::UC::NetworkItem *
  associatedItem(const Presonus::UC::NetworkItem &) const override {
    throw std::logic_error("unused");
  }
  void title(const Presonus::UC::NetworkItem &,
             Core::CStringBuffer<128> &) const override {
    throw std::logic_error("unused");
  }
  const char *host(const Presonus::UC::NetworkItem &) const override {
    throw std::logic_error("unused");
  }
  int targetType() const override { throw std::logic_error("unused"); }
  bool stored(const char *, Presonus::UC::NetworkItem *) const override {
    throw std::logic_error("unused");
  }
  void acquire(Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  void release(Presonus::UC::NetworkItem *, bool) override {
    throw std::logic_error("unused");
  }
  void *component(Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  void *mixerCast(void *) override { throw std::logic_error("unused"); }
  void *dawCast(void *) override { throw std::logic_error("unused"); }
  void setMixer(void *) override { throw std::logic_error("unused"); }
  void setDAW(void *) override { throw std::logic_error("unused"); }
  void setTransport(void *) override { throw std::logic_error("unused"); }
  void itemInfo(int, Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  void storeSelected(const char *, Presonus::UC::NetworkItem *, int) override {
    throw std::logic_error("unused");
  }
  void setNetworkRoot(Component *) override {
    throw std::logic_error("unused");
  }
  void selectModelItem(Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  int wiredAssignMode() const override { throw std::logic_error("unused"); }
  void configureNetwork(const char *) override {
    throw std::logic_error("unused");
  }
  void resumeAdaptors() override { throw std::logic_error("unused"); }
  void enableNetwork(bool) override { throw std::logic_error("unused"); }
  void setupLocalIP() override { throw std::logic_error("unused"); }
};

const char *safe(const char *s) { return s ? s : ""; }
void initialize(SettingFile &settings, const std::string &section,
                const std::string &key, const std::string &saved, int present,
                int valuePresent, int dirty) {
  settings.set("otherRoot", 111);
  if (present) {
    auto &s = settings.getSection(section.c_str());
    s.set("otherKey", 222);
    if (valuePresent)
      s.set(key.c_str(), saved.c_str());
  }
  settings.setDirty(dirty != 0);
}
void state(SettingFile &settings, const std::string &section,
           const std::string &key, int dirty, int result) {
  auto *s = settings.getAttributes(section.c_str());
  std::cout << "{\"section\":" << int(s != nullptr) << ",\"saved\":"
            << std::quoted(s ? safe(s->getString(key.c_str())) : "")
            << ",\"dirty\":" << dirty
            << ",\"otherRoot\":" << settings.getInt("otherRoot")
            << ",\"otherKey\":" << (s ? s->getInt("otherKey") : 0)
            << ",\"result\":" << result << "}" << std::endl;
}
// Direct pinned-CCL boundary interpreter. No reconstructed application method
// is called in this branch. Native ARM execution supplies the command order.
// Private lookupOrAdd is deferred until public makeAttributes/set, whose pinned
// implementations call lookupOrAdd then the observed AttributeValue operation.
int provider() {
  std::unique_ptr<SettingFile> settings;
  Attributes *sectionPtr = nullptr;
  std::string pendingID;
  bool pendingRoot = false;
  std::string section, key, command, text, other;
  int present, valuePresent, dirty, result;
  while (std::cin >> command) {
    if (command == "init") {
      std::cin >> std::quoted(section) >> std::quoted(key) >>
          std::quoted(text) >> present >> valuePresent >> dirty;
      settings = std::make_unique<SettingFile>();
      initialize(*settings, section, key, text, present, valuePresent, dirty);
      sectionPtr = nullptr;
      pendingID.clear();
      std::cout << "1" << std::endl;
    } else if (command == "section") {
      std::cin >> std::quoted(text);
      sectionPtr = settings->getAttributes(text.c_str());
      std::cout << int(sectionPtr != nullptr) << std::endl;
    } else if (command == "lookup") {
      int root;
      std::cin >> root >> std::quoted(text);
      pendingRoot = root != 0;
      pendingID = text;
      std::cout << "1" << std::endl;
    } else if (command == "make") {
      if (!pendingRoot)
        throw std::logic_error("unexpected nested creation");
      sectionPtr = settings->makeAttributes(pendingID.c_str());
      std::cout << "1" << std::endl;
    } else if (command == "set") {
      std::cin >> std::quoted(text);
      if (pendingRoot)
        throw std::logic_error("unexpected root string");
      sectionPtr->set(pendingID.c_str(), text.c_str(), false);
      std::cout << "1" << std::endl;
    } else if (command == "get") {
      std::cin >> std::quoted(text);
      std::cout << std::quoted(safe(sectionPtr->getString(text.c_str())))
                << std::endl;
    } else if (command == "buffer") {
      std::cin >> std::quoted(text);
      Core::CStringBuffer<64> buffer(text.c_str());
      std::cout << std::quoted(static_cast<const char *>(buffer)) << std::endl;
    } else if (command == "compare") {
      std::cin >> std::quoted(text) >> std::quoted(other);
      std::cout << std::strcmp(text.c_str(), other.c_str()) << std::endl;
    } else if (command == "state") {
      std::cin >> dirty >> result;
      state(*settings, section, key, dirty, result);
    } else
      throw std::logic_error("unknown provider operation");
  }
  return 0;
}
} // namespace
int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--provider")
    return provider();
  int method, present, valuePresent, flags, live, dirty;
  std::string section, key, saved, identity;
  while (std::cin >> method >> present >> valuePresent >> flags >> live >>
         dirty >> std::quoted(section) >> std::quoted(key) >>
         std::quoted(saved) >> std::quoted(identity)) {
    Component parameters;
    Dependencies dependencies;
    presonus::surface::SurfaceNetworkProvider network;
    Presonus::DelayTimer timer(0.f);
    presonus::surface::SurfaceNetworkState model{parameters, dependencies,
                                                 network, timer};
    SettingFile settings;
    initialize(settings, section, key, saved, present, valuePresent, dirty);
    model.settings = &settings;
    model.settingsSection = section.c_str();
    Presonus::Surface::NetworkSetupComponent component(model);
    int borrowed;
    Presonus::UC::NetworkItem item(&borrowed);
    item.setPortableIdentity(identity.c_str());
    int result = -1;
    if (method == 1)
      component.storeSelected(key.c_str(), live ? &item : nullptr, flags);
    else
      result = component.isStoredItem(key.c_str(), live ? &item : nullptr);
    if (item.getComponent() != &borrowed)
      throw std::logic_error("borrowed component changed");
    state(settings, section, key, settings.isDirty(), result);
  }
}

#include "core/portable/corepersistence.h"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <iostream>
#include <string>

using namespace Core::Portable;
using namespace Presonus::Surface;

namespace {
struct Settings : SettingFile {
  Settings() { filename = FileName("ui-settings.json"); }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const bool present = std::stoi(argv[1]) != 0;
  const bool dirty = std::stoi(argv[2]) != 0;
  Settings settings;
  if (present)
    settings.getSection("surface").set("obsolete", 11);
  settings.getSection("unrelated").set("keep", 5);
  settings.setDirty(dirty);

  static const ParamInfo infos[] = {
      PARAM_INT(3, "contrast", 0, 100, 0, 0, 0, 0, PARAM_STORABLE),
      PARAM_INT(4, "transient", 0, 100, 0, 0, 0, 0, 0)};
  Component tree("root");
  tree.addParameters(infos, 2);
  tree.getParameterByTag(3)->setValue(42.f);
  tree.getParameterByTag(4)->setValue(18.f);
  presonus::surface::RootServices services;
  services.rootParameters = &tree;
  services.settings = &settings;
  SurfaceRootComponent target;
  target.bindServices(services);
  target.storeSettings();
  const auto inspect = [](const SettingFile &file) {
    const auto *section = file.getAttributes("surface");
    const auto *unrelated = file.getAttributes("unrelated");
    if (!section || !unrelated)
      return false;
    std::cout << section->getInt("contrast") << ' '
              << section->contains("obsolete") << ' '
              << section->contains("transient") << ' '
              << unrelated->getInt("keep") << '\n';
    return true;
  };
  std::cout << "dirty " << settings.isDirty() << '\n';
  if (!inspect(settings))
    return 3;
  settings.storeIfNeeded();
  Settings restored;
  if (!restored.restore() || !inspect(restored))
    return 4;
  std::cout << "stored " << !settings.isDirty() << '\n';
}

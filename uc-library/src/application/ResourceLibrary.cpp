#include "presonus/application/ResourceLibrary.hpp"
#include <cstring>
#include <new>
#include <type_traits>

namespace Presonus {
ResourceLibrary::ResourceLibrary() : bundles_(0, 5) {}
ResourceLibrary::~ResourceLibrary() {
  static_assert(std::is_trivially_destructible<FirmwareBundle>::value);
  const int count = bundles_.count();
  FirmwareBundle **const items = bundles_.getItems();
  for (int index = 0; index < count; ++index)
    ::operator delete(static_cast<void *>(items[index]));
}
FirmwareBundle *ResourceLibrary::get(const char *name) {
  const int count = bundles_.count();
  FirmwareBundle **const items = bundles_.getItems();
  for (int index = 0; index < count; ++index) {
    auto *bundle = items[index];
    if (std::strcmp(bundle->name_.str(), name ? name : "") == 0)
      return bundle;
  }
  return nullptr;
}
unsigned int ResourceLibrary::getRequiredVersion(const char *name) {
  auto *bundle = get(name);
  return bundle ? bundle->version_ : 0;
}
void ResourceLibrary::addFirmware(const char *name, unsigned int version,
                                  const unsigned char *image, int size,
                                  bool compressed) {
  auto *bundle = new FirmwareBundle;
  bundle->name_ = name;
  bundle->version_ = version;
  bundle->image_ = image;
  bundle->image_size_ = size;
  bundle->compressed_ = compressed;
  addFirmware(bundle);
}
void ResourceLibrary::addFirmware(FirmwareBundle *bundle) {
  const int count = bundles_.count();
  if (count >= bundles_.getCapacity() && !bundles_.resize(count + 1))
    return;
  bundles_.add(bundle);
}
} // namespace Presonus

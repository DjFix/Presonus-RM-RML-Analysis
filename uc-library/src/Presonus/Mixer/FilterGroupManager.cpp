#include "presonus/mixer/FilterGroupManager.hpp"
namespace Presonus::Mixer {
FilterGroupManager::FilterGroupManager(const char *name)
    : Core::Portable::Component(name) {}
FilterGroupManager::~FilterGroupManager() = default;
} // namespace Presonus::Mixer

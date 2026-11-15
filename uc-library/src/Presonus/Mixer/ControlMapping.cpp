#include "presonus/mixer/ControlMapping.hpp"
namespace Presonus::Mixer {
ControlMapping::ControlMapping(Core::Portable::Parameter *parameter,
                               const char *name)
    : name_(name), parameter_(parameter) {}
} // namespace Presonus::Mixer

#include "presonus/mixer/AliasMapping.hpp"
namespace Presonus::Mixer {
AliasMapping::AliasMapping(Core::Portable::AliasParam *alias,
                           Core::Portable::Parameter *parameter,
                           const char *name)
    : ControlMapping(parameter, name), alias_(alias) {}
} // namespace Presonus::Mixer

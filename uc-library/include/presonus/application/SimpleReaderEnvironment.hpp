#pragma once
#include "presonus/application/ApplicationManagers.hpp"
#include "presonus/application/SimpleReader.hpp"

namespace presonus::startup {
// Supplies the actual recovered file reader. Concrete application construction
// and lifecycle endpoints remain abstract and are not replaced by dummy apps.
class SimpleReaderEnvironmentBindings : public CclEnvironmentBindings {
public:
  void readDeviceName(Core::CStringBuffer<64> &name,
                      const Core::ConstString &key,
                      const Core::ConstString &path) override {
    Presonus::SimpleReader::getValueForKey(name, key, path);
  }
};
} // namespace presonus::startup

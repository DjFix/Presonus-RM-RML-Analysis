#pragma once
#include "core/public/coreproperty.h"
#include "presonus/MeterMaid.hpp"
#include "presonus/MeterManagerBase.hpp"
namespace presonus::meter {
struct ManagerSourcePortTag {};
struct ManagerRosters {
  Core::Vector<Presonus::MeterMaid *> primary, sections, secondary;
  int word1564 = 0, word156c = 0, word1570 = 0, word1574 = 0, word1578 = 0;
  ManagerRosters() = default;
  ManagerRosters(const ManagerRosters &) = delete;
  ManagerRosters &operator=(const ManagerRosters &) = delete;
  ~ManagerRosters();
};
} // namespace presonus::meter
namespace Presonus {
// Independent tagged state integration; no original constructor or layout
// claim.
class MeterManager : public MeterManagerBase {
public:
  MeterManager(presonus::meter::ManagerSourcePortTag,
               presonus::meter::Environment *environment,
               UC::INetworkManager &network,
               presonus::meter::ManagerRosters &rosters)
      : MeterManagerBase(environment, network), rosters_(rosters) {}
  MeterMaid *getMeterMaid(int index, int selector, int kind);
  void getProperty(Core::Property &);
  void release();

private:
  presonus::meter::ManagerRosters &rosters_;
};
} // namespace Presonus

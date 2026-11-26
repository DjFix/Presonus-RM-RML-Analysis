#include "presonus/MeterManager.hpp"
namespace presonus::meter {
ManagerRosters::~ManagerRosters() {
  for (auto *roster : {&primary, &sections, &secondary}) {
    for (int i = 0; i < roster->count(); ++i)
      delete roster->at(i);
    roster->removeAll();
  }
}
} // namespace presonus::meter
namespace Presonus {
void MeterManager::getProperty(Core::Property &) {}
void MeterManager::release() {}
MeterMaid *MeterManager::getMeterMaid(int index, int selector, int kind) {
  auto *roster = &rosters_.primary;
  switch (selector) {
  case 0:
    break;
  case 1:
    index = index * 2 + rosters_.word1564;
    break;
  case 4:
    roster = &rosters_.sections;
    break;
  case 5:
    roster = &rosters_.sections;
    index += rosters_.word156c;
    break;
  case 6:
    roster = &rosters_.sections;
    index += rosters_.word156c + rosters_.word1570;
    break;
  case 7:
    roster = &rosters_.sections;
    index += rosters_.word156c + rosters_.word1570 + rosters_.word1574 +
             (kind == 4 ? 1 : 0);
    break;
  case 8:
    roster = &rosters_.sections;
    index += rosters_.word156c + rosters_.word1570 + rosters_.word1574 +
             rosters_.word1578;
    break;
  default:
    index = -1;
    break;
  }
  if (roster == &rosters_.primary && kind == 1)
    roster = &rosters_.secondary;
  MeterMaid *result = index < roster->count() ? roster->at(index) : nullptr;
  if (!result) {
    result = new MeterMaid;
    roster->add(result);
  }
  if (roster == &rosters_.primary && kind == 3)
    result->state_.mode = true;
  return result;
}
} // namespace Presonus

#include "presonus/panel/SPIControlGroup.hpp"
#include "presonus/panel/control.hpp"
#include <cstdlib>
#include <iostream>
#include <memory>
namespace {
int destroyed = 0;
struct Borrowed : Presonus::Panel::Control {
  Borrowed() : Control(9) {}
  ~Borrowed() override { ++destroyed; }
};
void require(bool value) {
  if (!value)
    std::abort();
}
} // namespace
struct NoTransfer : presonus::spi_port::Transfer {
  void submit(int, std::uint32_t, const std::uint8_t *, std::uint8_t *,
              int) override {
    std::abort();
  }
};
int main() {
  Core::FixedSizeVector<std::uint32_t, 1> words;
  NoTransfer transfer;
  auto control = std::make_unique<Borrowed>();
  {
    auto group = std::make_unique<Presonus::Panel::SPIControlGroup>(
        words, 3, -1, transfer);
    group->add(control.get());
    require(presonus::panel::ControlAccess::io(*control) ==
            static_cast<Presonus::Panel::IPanelIO *>(group.get()));
    require(group->count() == 1);
  }
  require(destroyed == 0);
  control.reset();
  require(destroyed == 1);
  for (bool full : {false, true}) {
    auto retained = std::make_unique<Borrowed>();
    {
      auto group = std::make_unique<Presonus::Panel::SPIControlGroup>(1, 0, 3);
      if (full)
        for (int i = 0; i < 256; ++i)
          group->ControlGroup::add(nullptr);
      group->add(retained.get());
      require(presonus::panel::ControlAccess::io(*retained) ==
              static_cast<Presonus::Panel::IPanelIO *>(group.get()));
      require(group->count() == (full ? 256 : 1));
      if (!full)
        retained.release();
    }
    require(destroyed == 2);
    retained.reset();
  }
  require(destroyed == 3);
  std::cout << "production add owns inserted heap controls, full capacity "
               "preserves caller ownership, explicit borrowed constructor "
               "preserves borrowed controls; actual "
               "child destructor executes once\n";
}

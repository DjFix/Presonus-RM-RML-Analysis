#include "../recovered-all/client/symbols.hpp"
#include "../recovered-all/server/symbols.hpp"
#include "../recovered-dice/client/symbols.hpp"
#include "../recovered-dice/server/symbols.hpp"
#include "../recovered/client/symbols.hpp"
#include "../recovered/server/symbols.hpp"
static_assert(presonus::uc::recovered::client::symbol_count == 2568);
static_assert(presonus::uc::recovered::server::symbol_count == 2659);
static_assert(presonus::firmware::recovered::dice::client::symbol_count == 143);
static_assert(presonus::firmware::recovered::dice::server::symbol_count == 37);
static_assert(presonus::firmware::recovered::all::client::symbol_count ==
              11964);
static_assert(presonus::firmware::recovered::all::server::symbol_count ==
              11521);

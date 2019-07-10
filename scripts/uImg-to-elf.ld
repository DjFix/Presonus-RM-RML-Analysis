ENTRY(_start);

SECTIONS
{
    _start = 0x00000;
    . = 0x00000;
    .data : {
        *(.data)
    }
}
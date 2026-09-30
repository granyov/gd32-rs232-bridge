/* Bare-metal newlib hooks: startup calls __libc_init_array; no CRT startup
 * object or semihosting is linked. There are no platform constructors. */
void _init(void) {}
void _fini(void) {}

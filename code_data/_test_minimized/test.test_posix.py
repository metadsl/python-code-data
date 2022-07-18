class PosixTester(unittest.TestCase):

    def setUp(self):
        # create empty file
        with open(os_helper.TESTFN, "wb"):
            pass
        self.teardown_files = [ os_helper.TESTFN ]
        self._warnings_manager = warnings_helper.check_warnings()
        self._warnings_manager.__enter__()
        warnings.filterwarnings('ignore', '.* potential security risk .*',
                                RuntimeWarning)

    def tearDown(self):
        for teardown_file in self.teardown_files:
            os_helper.unlink(teardown_file)
        self._warnings_manager.__exit__(None, None, None)

    def testNoArgFunctions(self):
        # test posix functions which take no arguments and have
        # no side-effects which we need to cleanup (e.g., fork, wait, abort)
        NO_ARG_FUNCTIONS = [ "ctermid", "getcwd", "getcwdb", "uname",
                             "times", "getloadavg",
                             "getegid", "geteuid", "getgid", "getgroups",
                             "getpid", "getpgrp", "getppid", "getuid", "sync",
                           ]

        for name in NO_ARG_FUNCTIONS:
            posix_func = getattr(posix, name, None)
            if posix_func is not None:
                posix_func()
                self.assertRaises(TypeError, posix_func, 1)

    @unittest.skipUnless(hasattr(posix, 'getresuid'),
                         'test needs posix.getresuid()')
    def test_getresuid(self):
        user_ids = posix.getresuid()
        self.assertEqual(len(user_ids), 3)
        for val in user_ids:
            self.assertGreaterEqual(val, 0)

    @unittest.skipUnless(hasattr(posix, 'getresgid'),
                         'test needs posix.getresgid()')
    def test_getresgid(self):
        group_ids = posix.getresgid()
        self.assertEqual(len(group_ids), 3)
        for val in group_ids:
            self.assertGreaterEqual(val, 0)

    @unittest.skipUnless(hasattr(posix, 'setresuid'),
                         'test needs posix.setresuid()')
    def test_setresuid(self):
        current_user_ids = posix.getresuid()
        self.assertIsNone(posix.setresuid(*current_user_ids))
        # -1 means don't change that value.
        self.assertIsNone(posix.setresuid(-1, -1, -1))

    @unittest.skipUnless(hasattr(posix, 'setresuid'),
                         'test needs posix.setresuid()')
    def test_setresuid_exception(self):
        # Don't do this test if someone is silly enough to run us as root.
        current_user_ids = posix.getresuid()
        if 0 not in current_user_ids:
            new_user_ids = (current_user_ids[0]+1, -1, -1)
            self.assertRaises(OSError, posix.setresuid, *new_user_ids)

    @unittest.skipUnless(hasattr(posix, 'setresgid'),
                         'test needs posix.setresgid()')
    def test_setresgid(self):
        current_group_ids = posix.getresgid()
        self.assertIsNone(posix.setresgid(*current_group_ids))
        # -1 means don't change that value.
        self.assertIsNone(posix.setresgid(-1, -1, -1))

    @unittest.skipUnless(hasattr(posix, 'setresgid'),
                         'test needs posix.setresgid()')
    def test_setresgid_exception(self):
        # Don't do this test if someone is silly enough to run us as root.
        current_group_ids = posix.getresgid()
        if 0 not in current_group_ids:
            new_group_ids = (current_group_ids[0]+1, -1, -1)
            self.assertRaises(OSError, posix.setresgid, *new_group_ids)

    @unittest.skipUnless(hasattr(posix, 'initgroups'),
                         "test needs os.initgroups()")
    def test_initgroups(self):
        # It takes a string and an integer; check that it raises a TypeError
        # for other argument lists.
        self.assertRaises(TypeError, posix.initgroups)
        self.assertRaises(TypeError, posix.initgroups, None)
        self.assertRaises(TypeError, posix.initgroups, 3, "foo")
        self.assertRaises(TypeError, posix.initgroups, "foo", 3, object())

        # If a non-privileged user invokes it, it should fail with OSError
        # EPERM.
        if os.getuid() != 0:
            try:
                name = pwd.getpwuid(posix.getuid()).pw_name
            except KeyError:
                # the current UID may not have a pwd entry
                raise unittest.SkipTest("need a pwd entry")
            try:
                posix.initgroups(name, 13)
            except OSError as e:
                self.assertEqual(e.errno, errno.EPERM)
            else:
                self.fail("Expected OSError to be raised by initgroups")

    @unittest.skipUnless(hasattr(posix, 'statvfs'),
                         'test needs posix.statvfs()')
    def test_statvfs(self):
        self.assertTrue(posix.statvfs(os.curdir))

    @unittest.skipUnless(hasattr(posix, 'fstatvfs'),
                         'test needs posix.fstatvfs()')
    def test_fstatvfs(self):
        fp = open(os_helper.TESTFN)
        try:
            self.assertTrue(posix.fstatvfs(fp.fileno()))
            self.assertTrue(posix.statvfs(fp.fileno()))
        finally:
            fp.close()

    @unittest.skipUnless(hasattr(posix, 'ftruncate'),
                         'test needs posix.ftruncate()')
    def test_ftruncate(self):
        fp = open(os_helper.TESTFN, 'w+')
        try:
            # we need to have some data to truncate
            fp.write('test')
            fp.flush()
            posix.ftruncate(fp.fileno(), 0)
        finally:
            fp.close()

    @unittest.skipUnless(hasattr(posix, 'truncate'), "test needs posix.truncate()")
    def test_truncate(self):
        with open(os_helper.TESTFN, 'w') as fp:
            fp.write('test')
            fp.flush()
        posix.truncate(os_helper.TESTFN, 0)

    @unittest.skipUnless(getattr(os, 'execve', None) in os.supports_fd, "test needs execve() to support the fd parameter")
    @unittest.skipUnless(hasattr(os, 'fork'), "test needs os.fork()")
    def test_fexecve(self):
        fp = os.open(sys.executable, os.O_RDONLY)
        try:
            pid = os.fork()
            if pid == 0:
                os.chdir(os.path.split(sys.executable)[0])
                posix.execve(fp, [sys.executable, '-c', 'pass'], os.environ)
            else:
                support.wait_process(pid, exitcode=0)
        finally:
            os.close(fp)


    @unittest.skipUnless(hasattr(posix, 'waitid'), "test needs posix.waitid()")
    @unittest.skipUnless(hasattr(os, 'fork'), "test needs os.fork()")
    def test_waitid(self):
        pid = os.fork()
        if pid == 0:
            os.chdir(os.path.split(sys.executable)[0])
            posix.execve(sys.executable, [sys.executable, '-c', 'pass'], os.environ)
        else:
            res = posix.waitid(posix.P_PID, pid, posix.WEXITED)
            self.assertEqual(pid, res.si_pid)

    @unittest.skipUnless(hasattr(os, 'fork'), "test needs os.fork()")
    def test_register_at_fork(self):
        with self.assertRaises(TypeError, msg="Positional args not allowed"):
            os.register_at_fork(lambda: None)
        with self.assertRaises(TypeError, msg="Args must be callable"):
            os.register_at_fork(before=2)
        with self.assertRaises(TypeError, msg="Args must be callable"):
            os.register_at_fork(after_in_child="three")
        with self.assertRaises(TypeError, msg="Args must be callable"):
            os.register_at_fork(after_in_parent=b"Five")
        with self.assertRaises(TypeError, msg="Args must not be None"):
            os.register_at_fork(before=None)
        with self.assertRaises(TypeError, msg="Args must not be None"):
            os.register_at_fork(after_in_child=None)
        with self.assertRaises(TypeError, msg="Args must not be None"):
            os.register_at_fork(after_in_parent=None)
        with self.assertRaises(TypeError, msg="Invalid arg was allowed"):
            # Ensure a combination of valid and invalid is an error.
            os.register_at_fork(before=None, after_in_parent=lambda: 3)
        with self.assertRaises(TypeError, msg="Invalid arg was allowed"):
            # Ensure a combination of valid and invalid is an error.
            os.register_at_fork(before=lambda: None, after_in_child='')
        # We test actual registrations in their own process so as not to
        # pollute this one.  There is no way to unregister for cleanup.
        code = """if 1:
            import os

            r, w = os.pipe()
            fin_r, fin_w = os.pipe()

            os.register_at_fork(before=lambda: os.write(w, b'A'))
            os.register_at_fork(after_in_parent=lambda: os.write(w, b'C'))
            os.register_at_fork(after_in_child=lambda: os.write(w, b'E'))
            os.register_at_fork(before=lambda: os.write(w, b'B'),
                                after_in_parent=lambda: os.write(w, b'D'),
                                after_in_child=lambda: os.write(w, b'F'))

            pid = os.fork()
            if pid == 0:
                # At this point, after-forkers have already been executed
                os.close(w)
                # Wait for parent to tell us to exit
                os.read(fin_r, 1)
                os._exit(0)
            else:
                try:
                    os.close(w)
                    with open(r, "rb") as f:
                        data = f.read()
                        assert len(data) == 6, data
                        # Check before-fork callbacks
                        assert data[:2] == b'BA', data
                        # Check after-fork callbacks
                        assert sorted(data[2:]) == list(b'CDEF'), data
                        assert data.index(b'C') < data.index(b'D'), data
                        assert data.index(b'E') < data.index(b'F'), data
                finally:
                    os.write(fin_w, b'!')
            """
        assert_python_ok('-c', code)

    @unittest.skipUnless(hasattr(posix, 'lockf'), "test needs posix.lockf()")
    def test_lockf(self):
        fd = os.open(os_helper.TESTFN, os.O_WRONLY | os.O_CREAT)
        try:
            os.write(fd, b'test')
            os.lseek(fd, 0, os.SEEK_SET)
            posix.lockf(fd, posix.F_LOCK, 4)
            # section is locked
            posix.lockf(fd, posix.F_ULOCK, 4)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'pread'), "test needs posix.pread()")
    def test_pread(self):
        fd = os.open(os_helper.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd, b'test')
            os.lseek(fd, 0, os.SEEK_SET)
            self.assertEqual(b'es', posix.pread(fd, 2, 1))
            # the first pread() shouldn't disturb the file offset
            self.assertEqual(b'te', posix.read(fd, 2))
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'preadv'), "test needs posix.preadv()")
    def test_preadv(self):
        fd = os.open(os_helper.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd, b'test1tt2t3t5t6t6t8')
            buf = [bytearray(i) for i in [5, 3, 2]]
            self.assertEqual(posix.preadv(fd, buf, 3), 10)
            self.assertEqual([b't1tt2', b't3t', b'5t'], list(buf))
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'preadv'), "test needs posix.preadv()")
    @unittest.skipUnless(hasattr(posix, 'RWF_HIPRI'), "test needs posix.RWF_HIPRI")
    def test_preadv_flags(self):
        fd = os.open(os_helper.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd, b'test1tt2t3t5t6t6t8')
            buf = [bytearray(i) for i in [5, 3, 2]]
            self.assertEqual(posix.preadv(fd, buf, 3, os.RWF_HIPRI), 10)
            self.assertEqual([b't1tt2', b't3t', b'5t'], list(buf))
        except NotImplementedError:
            self.skipTest("preadv2 not available")
        except OSError as inst:
            # Is possible that the macro RWF_HIPRI was defined at compilation time
            # but the option is not supported by the kernel or the runtime libc shared
            # library.
            if inst.errno in {errno.EINVAL, errno.ENOTSUP}:
                raise unittest.SkipTest("RWF_HIPRI is not supported by the current system")
            else:
                raise
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'preadv'), "test needs posix.preadv()")
    @requires_32b
    def test_preadv_overflow_32bits(self):
        fd = os.open(os_helper.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            buf = [bytearray(2**16)] * 2**15
            with self.assertRaises(OSError) as cm:
                os.preadv(fd, buf, 0)
            self.assertEqual(cm.exception.errno, errno.EINVAL)
            self.assertEqual(bytes(buf[0]), b'\0'* 2**16)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'pwrite'), "test needs posix.pwrite()")
    def test_pwrite(self):
        fd = os.open(os_helper.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd, b'test')
            os.lseek(fd, 0, os.SEEK_SET)
            posix.pwrite(fd, b'xx', 1)
            self.assertEqual(b'txxt', posix.read(fd, 4))
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'pwritev'), "test needs posix.pwritev()")
    def test_pwritev(self):
        fd = os.open(os_helper.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd, b"xx")
            os.lseek(fd, 0, os.SEEK_SET)
            n = os.pwritev(fd, [b'test1', b'tt2', b't3'], 2)
            self.assertEqual(n, 10)

            os.lseek(fd, 0, os.SEEK_SET)
            self.assertEqual(b'xxtest1tt2t3', posix.read(fd, 100))
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'pwritev'), "test needs posix.pwritev()")
    @unittest.skipUnless(hasattr(posix, 'os.RWF_SYNC'), "test needs os.RWF_SYNC")
    def test_pwritev_flags(self):
        fd = os.open(os_helper.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd,b"xx")
            os.lseek(fd, 0, os.SEEK_SET)
            n = os.pwritev(fd, [b'test1', b'tt2', b't3'], 2, os.RWF_SYNC)
            self.assertEqual(n, 10)

            os.lseek(fd, 0, os.SEEK_SET)
            self.assertEqual(b'xxtest1tt2', posix.read(fd, 100))
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'pwritev'), "test needs posix.pwritev()")
    @requires_32b
    def test_pwritev_overflow_32bits(self):
        fd = os.open(os_helper.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            with self.assertRaises(OSError) as cm:
                os.pwritev(fd, [b"x" * 2**16] * 2**15, 0)
            self.assertEqual(cm.exception.errno, errno.EINVAL)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'posix_fallocate'),
        "test needs posix.posix_fallocate()")
    def test_posix_fallocate(self):
        fd = os.open(os_helper.TESTFN, os.O_WRONLY | os.O_CREAT)
        try:
            posix.posix_fallocate(fd, 0, 10)
        except OSError as inst:
            # issue10812, ZFS doesn't appear to support posix_fallocate,
            # so skip Solaris-based since they are likely to have ZFS.
            # issue33655: Also ignore EINVAL on *BSD since ZFS is also
            # often used there.
            if inst.errno == errno.EINVAL and sys.platform.startswith(
                ('sunos', 'freebsd', 'netbsd', 'openbsd', 'gnukfreebsd')):
                raise unittest.SkipTest("test may fail on ZFS filesystems")
            else:
                raise
        finally:
            os.close(fd)

    # issue31106 - posix_fallocate() does not set error in errno.
    @unittest.skipUnless(hasattr(posix, 'posix_fallocate'),
        "test needs posix.posix_fallocate()")
    def test_posix_fallocate_errno(self):
        try:
            posix.posix_fallocate(-42, 0, 10)
        except OSError as inst:
            if inst.errno != errno.EBADF:
                raise

    @unittest.skipUnless(hasattr(posix, 'posix_fadvise'),
        "test needs posix.posix_fadvise()")
    def test_posix_fadvise(self):
        fd = os.open(os_helper.TESTFN, os.O_RDONLY)
        try:
            posix.posix_fadvise(fd, 0, 0, posix.POSIX_FADV_WILLNEED)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'posix_fadvise'),
        "test needs posix.posix_fadvise()")
    def test_posix_fadvise_errno(self):
        try:
            posix.posix_fadvise(-42, 0, 0, posix.POSIX_FADV_WILLNEED)
        except OSError as inst:
            if inst.errno != errno.EBADF:
                raise

    @unittest.skipUnless(os.utime in os.supports_fd, "test needs fd support in os.utime")
    def test_utime_with_fd(self):
        now = time.time()
        fd = os.open(os_helper.TESTFN, os.O_RDONLY)
        try:
            posix.utime(fd)
            posix.utime(fd, None)
            self.assertRaises(TypeError, posix.utime, fd, (None, None))
            self.assertRaises(TypeError, posix.utime, fd, (now, None))
            self.assertRaises(TypeError, posix.utime, fd, (None, now))
            posix.utime(fd, (int(now), int(now)))
            posix.utime(fd, (now, now))
            self.assertRaises(ValueError, posix.utime, fd, (now, now), ns=(now, now))
            self.assertRaises(ValueError, posix.utime, fd, (now, 0), ns=(None, None))
            self.assertRaises(ValueError, posix.utime, fd, (None, None), ns=(now, 0))
            posix.utime(fd, (int(now), int((now - int(now)) * 1e9)))
            posix.utime(fd, ns=(int(now), int((now - int(now)) * 1e9)))

        finally:
            os.close(fd)

    @unittest.skipUnless(os.utime in os.supports_follow_symlinks, "test needs follow_symlinks support in os.utime")
    def test_utime_nofollow_symlinks(self):
        now = time.time()
        posix.utime(os_helper.TESTFN, None, follow_symlinks=False)
        self.assertRaises(TypeError, posix.utime, os_helper.TESTFN,
                          (None, None), follow_symlinks=False)
        self.assertRaises(TypeError, posix.utime, os_helper.TESTFN,
                          (now, None), follow_symlinks=False)
        self.assertRaises(TypeError, posix.utime, os_helper.TESTFN,
                          (None, now), follow_symlinks=False)
        posix.utime(os_helper.TESTFN, (int(now), int(now)),
                    follow_symlinks=False)
        posix.utime(os_helper.TESTFN, (now, now), follow_symlinks=False)
        posix.utime(os_helper.TESTFN, follow_symlinks=False)

    @unittest.skipUnless(hasattr(posix, 'writev'), "test needs posix.writev()")
    def test_writev(self):
        fd = os.open(os_helper.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            n = os.writev(fd, (b'test1', b'tt2', b't3'))
            self.assertEqual(n, 10)

            os.lseek(fd, 0, os.SEEK_SET)
            self.assertEqual(b'test1tt2t3', posix.read(fd, 10))

            # Issue #20113: empty list of buffers should not crash
            try:
                size = posix.writev(fd, [])
            except OSError:
                # writev(fd, []) raises OSError(22, "Invalid argument")
                # on OpenIndiana
                pass
            else:
                self.assertEqual(size, 0)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'writev'), "test needs posix.writev()")
    @requires_32b
    def test_writev_overflow_32bits(self):
        fd = os.open(os_helper.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            with self.assertRaises(OSError) as cm:
                os.writev(fd, [b"x" * 2**16] * 2**15)
            self.assertEqual(cm.exception.errno, errno.EINVAL)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'readv'), "test needs posix.readv()")
    def test_readv(self):
        fd = os.open(os_helper.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd, b'test1tt2t3')
            os.lseek(fd, 0, os.SEEK_SET)
            buf = [bytearray(i) for i in [5, 3, 2]]
            self.assertEqual(posix.readv(fd, buf), 10)
            self.assertEqual([b'test1', b'tt2', b't3'], [bytes(i) for i in buf])

            # Issue #20113: empty list of buffers should not crash
            try:
                size = posix.readv(fd, [])
            except OSError:
                # readv(fd, []) raises OSError(22, "Invalid argument")
                # on OpenIndiana
                pass
            else:
                self.assertEqual(size, 0)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'readv'), "test needs posix.readv()")
    @requires_32b
    def test_readv_overflow_32bits(self):
        fd = os.open(os_helper.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            buf = [bytearray(2**16)] * 2**15
            with self.assertRaises(OSError) as cm:
                os.readv(fd, buf)
            self.assertEqual(cm.exception.errno, errno.EINVAL)
            self.assertEqual(bytes(buf[0]), b'\0'* 2**16)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'dup'),
                         'test needs posix.dup()')
    def test_dup(self):
        fp = open(os_helper.TESTFN)
        try:
            fd = posix.dup(fp.fileno())
            self.assertIsInstance(fd, int)
            os.close(fd)
        finally:
            fp.close()

    @unittest.skipUnless(hasattr(posix, 'confstr'),
                         'test needs posix.confstr()')
    def test_confstr(self):
        self.assertRaises(ValueError, posix.confstr, "CS_garbage")
        self.assertEqual(len(posix.confstr("CS_PATH")) > 0, True)

    @unittest.skipUnless(hasattr(posix, 'dup2'),
                         'test needs posix.dup2()')
    def test_dup2(self):
        fp1 = open(os_helper.TESTFN)
        fp2 = open(os_helper.TESTFN)
        try:
            posix.dup2(fp1.fileno(), fp2.fileno())
        finally:
            fp1.close()
            fp2.close()

    @unittest.skipUnless(hasattr(os, 'O_CLOEXEC'), "needs os.O_CLOEXEC")
    @support.requires_linux_version(2, 6, 23)
    def test_oscloexec(self):
        fd = os.open(os_helper.TESTFN, os.O_RDONLY|os.O_CLOEXEC)
        self.addCleanup(os.close, fd)
        self.assertFalse(os.get_inheritable(fd))

    @unittest.skipUnless(hasattr(posix, 'O_EXLOCK'),
                         'test needs posix.O_EXLOCK')
    def test_osexlock(self):
        fd = os.open(os_helper.TESTFN,
                     os.O_WRONLY|os.O_EXLOCK|os.O_CREAT)
        self.assertRaises(OSError, os.open, os_helper.TESTFN,
                          os.O_WRONLY|os.O_EXLOCK|os.O_NONBLOCK)
        os.close(fd)

        if hasattr(posix, "O_SHLOCK"):
            fd = os.open(os_helper.TESTFN,
                         os.O_WRONLY|os.O_SHLOCK|os.O_CREAT)
            self.assertRaises(OSError, os.open, os_helper.TESTFN,
                              os.O_WRONLY|os.O_EXLOCK|os.O_NONBLOCK)
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'O_SHLOCK'),
                         'test needs posix.O_SHLOCK')
    def test_osshlock(self):
        fd1 = os.open(os_helper.TESTFN,
                     os.O_WRONLY|os.O_SHLOCK|os.O_CREAT)
        fd2 = os.open(os_helper.TESTFN,
                      os.O_WRONLY|os.O_SHLOCK|os.O_CREAT)
        os.close(fd2)
        os.close(fd1)

        if hasattr(posix, "O_EXLOCK"):
            fd = os.open(os_helper.TESTFN,
                         os.O_WRONLY|os.O_SHLOCK|os.O_CREAT)
            self.assertRaises(OSError, os.open, os_helper.TESTFN,
                              os.O_RDONLY|os.O_EXLOCK|os.O_NONBLOCK)
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'fstat'),
                         'test needs posix.fstat()')
    def test_fstat(self):
        fp = open(os_helper.TESTFN)
        try:
            self.assertTrue(posix.fstat(fp.fileno()))
            self.assertTrue(posix.stat(fp.fileno()))

            self.assertRaisesRegex(TypeError,
                    'should be string, bytes, os.PathLike or integer, not',
                    posix.stat, float(fp.fileno()))
        finally:
            fp.close()

    def test_stat(self):
        self.assertTrue(posix.stat(os_helper.TESTFN))
        self.assertTrue(posix.stat(os.fsencode(os_helper.TESTFN)))

        self.assertWarnsRegex(DeprecationWarning,
                'should be string, bytes, os.PathLike or integer, not',
                posix.stat, bytearray(os.fsencode(os_helper.TESTFN)))
        self.assertRaisesRegex(TypeError,
                'should be string, bytes, os.PathLike or integer, not',
                posix.stat, None)
        self.assertRaisesRegex(TypeError,
                'should be string, bytes, os.PathLike or integer, not',
                posix.stat, list(os_helper.TESTFN))
        self.assertRaisesRegex(TypeError,
                'should be string, bytes, os.PathLike or integer, not',
                posix.stat, list(os.fsencode(os_helper.TESTFN)))

    @unittest.skipUnless(hasattr(posix, 'mkfifo'), "don't have mkfifo()")
    def test_mkfifo(self):
        if sys.platform == "vxworks":
            fifo_path = os.path.join("/fifos/", os_helper.TESTFN)
        else:
            fifo_path = os_helper.TESTFN
        os_helper.unlink(fifo_path)
        self.addCleanup(os_helper.unlink, fifo_path)
        try:
            posix.mkfifo(fifo_path, stat.S_IRUSR | stat.S_IWUSR)
        except PermissionError as e:
            self.skipTest('posix.mkfifo(): %s' % e)
        self.assertTrue(stat.S_ISFIFO(posix.stat(fifo_path).st_mode))

    @unittest.skipUnless(hasattr(posix, 'mknod') and hasattr(stat, 'S_IFIFO'),
                         "don't have mknod()/S_IFIFO")
    def test_mknod(self):
        # Test using mknod() to create a FIFO (the only use specified
        # by POSIX).
        os_helper.unlink(os_helper.TESTFN)
        mode = stat.S_IFIFO | stat.S_IRUSR | stat.S_IWUSR
        try:
            posix.mknod(os_helper.TESTFN, mode, 0)
        except OSError as e:
            # Some old systems don't allow unprivileged users to use
            # mknod(), or only support creating device nodes.
            self.assertIn(e.errno, (errno.EPERM, errno.EINVAL, errno.EACCES))
        else:
            self.assertTrue(stat.S_ISFIFO(posix.stat(os_helper.TESTFN).st_mode))

        # Keyword arguments are also supported
        os_helper.unlink(os_helper.TESTFN)
        try:
            posix.mknod(path=os_helper.TESTFN, mode=mode, device=0,
                dir_fd=None)
        except OSError as e:
            self.assertIn(e.errno, (errno.EPERM, errno.EINVAL, errno.EACCES))

    @unittest.skipUnless(hasattr(posix, 'makedev'), 'test needs posix.makedev()')
    def test_makedev(self):
        st = posix.stat(os_helper.TESTFN)
        dev = st.st_dev
        self.assertIsInstance(dev, int)
        self.assertGreaterEqual(dev, 0)

        major = posix.major(dev)
        self.assertIsInstance(major, int)
        self.assertGreaterEqual(major, 0)
        self.assertEqual(posix.major(dev), major)
        self.assertRaises(TypeError, posix.major, float(dev))
        self.assertRaises(TypeError, posix.major)
        self.assertRaises((ValueError, OverflowError), posix.major, -1)

        minor = posix.minor(dev)
        self.assertIsInstance(minor, int)
        self.assertGreaterEqual(minor, 0)
        self.assertEqual(posix.minor(dev), minor)
        self.assertRaises(TypeError, posix.minor, float(dev))
        self.assertRaises(TypeError, posix.minor)
        self.assertRaises((ValueError, OverflowError), posix.minor, -1)

        self.assertEqual(posix.makedev(major, minor), dev)
        self.assertRaises(TypeError, posix.makedev, float(major), minor)
        self.assertRaises(TypeError, posix.makedev, major, float(minor))
        self.assertRaises(TypeError, posix.makedev, major)
        self.assertRaises(TypeError, posix.makedev)

    def _test_all_chown_common(self, chown_func, first_param, stat_func):
        """Common code for chown, fchown and lchown tests."""
        def check_stat(uid, gid):
            if stat_func is not None:
                stat = stat_func(first_param)
                self.assertEqual(stat.st_uid, uid)
                self.assertEqual(stat.st_gid, gid)
        uid = os.getuid()
        gid = os.getgid()
        # test a successful chown call
        chown_func(first_param, uid, gid)
        check_stat(uid, gid)
        chown_func(first_param, -1, gid)
        check_stat(uid, gid)
        chown_func(first_param, uid, -1)
        check_stat(uid, gid)

        if sys.platform == "vxworks":
            # On VxWorks, root user id is 1 and 0 means no login user:
            # both are super users.
            is_root = (uid in (0, 1))
        else:
            is_root = (uid == 0)
        if is_root:
            # Try an amusingly large uid/gid to make sure we handle
            # large unsigned values.  (chown lets you use any
            # uid/gid you like, even if they aren't defined.)
            #
            # On VxWorks uid_t is defined as unsigned short. A big
            # value greater than 65535 will result in underflow error.
            #
            # This problem keeps coming up:
            #   http://bugs.python.org/issue1747858
            #   http://bugs.python.org/issue4591
            #   http://bugs.python.org/issue15301
            # Hopefully the fix in 4591 fixes it for good!
            #
            # This part of the test only runs when run as root.
            # Only scary people run their tests as root.

            big_value = (2**31 if sys.platform != "vxworks" else 2**15)
            chown_func(first_param, big_value, big_value)
            check_stat(big_value, big_value)
            chown_func(first_param, -1, -1)
            check_stat(big_value, big_value)
            chown_func(first_param, uid, gid)
            check_stat(uid, gid)
        elif platform.system() in ('HP-UX', 'SunOS'):
            # HP-UX and Solaris can allow a non-root user to chown() to root
            # (issue #5113)
            raise unittest.SkipTest("Skipping because of non-standard chown() "
                                    "behavior")
        else:
            # non-root cannot chown to root, raises OSError
            self.assertRaises(OSError, chown_func, first_param, 0, 0)
            check_stat(uid, gid)
            self.assertRaises(OSError, chown_func, first_param, 0, -1)
            check_stat(uid, gid)
            if 0 not in os.getgroups():
                self.assertRaises(OSError, chown_func, first_param, -1, 0)
                check_stat(uid, gid)
        # test illegal types
        for t in str, float:
            self.assertRaises(TypeError, chown_func, first_param, t(uid), gid)
            check_stat(uid, gid)
            self.assertRaises(TypeError, chown_func, first_param, uid, t(gid))
            check_stat(uid, gid)

    @unittest.skipUnless(hasattr(posix, 'chown'), "test needs os.chown()")
    def test_chown(self):
        # raise an OSError if the file does not exist
        os.unlink(os_helper.TESTFN)
        self.assertRaises(OSError, posix.chown, os_helper.TESTFN, -1, -1)

        # re-create the file
        os_helper.create_empty_file(os_helper.TESTFN)
        self._test_all_chown_common(posix.chown, os_helper.TESTFN, posix.stat)

    @unittest.skipUnless(hasattr(posix, 'fchown'), "test needs os.fchown()")
    def test_fchown(self):
        os.unlink(os_helper.TESTFN)

        # re-create the file
        test_file = open(os_helper.TESTFN, 'w')
        try:
            fd = test_file.fileno()
            self._test_all_chown_common(posix.fchown, fd,
                                        getattr(posix, 'fstat', None))
        finally:
            test_file.close()

    @unittest.skipUnless(hasattr(posix, 'lchown'), "test needs os.lchown()")
    def test_lchown(self):
        os.unlink(os_helper.TESTFN)
        # create a symlink
        os.symlink(_DUMMY_SYMLINK, os_helper.TESTFN)
        self._test_all_chown_common(posix.lchown, os_helper.TESTFN,
                                    getattr(posix, 'lstat', None))

    @unittest.skipUnless(hasattr(posix, 'chdir'), 'test needs posix.chdir()')
    def test_chdir(self):
        posix.chdir(os.curdir)
        self.assertRaises(OSError, posix.chdir, os_helper.TESTFN)

    def test_listdir(self):
        self.assertIn(os_helper.TESTFN, posix.listdir(os.curdir))

    def test_listdir_default(self):
        # When listdir is called without argument,
        # it's the same as listdir(os.curdir).
        self.assertIn(os_helper.TESTFN, posix.listdir())

    def test_listdir_bytes(self):
        # When listdir is called with a bytes object,
        # the returned strings are of type bytes.
        self.assertIn(os.fsencode(os_helper.TESTFN), posix.listdir(b'.'))

    def test_listdir_bytes_like(self):
        for cls in bytearray, memoryview:
            with self.assertWarns(DeprecationWarning):
                names = posix.listdir(cls(b'.'))
            self.assertIn(os.fsencode(os_helper.TESTFN), names)
            for name in names:
                self.assertIs(type(name), bytes)

    @unittest.skipUnless(posix.listdir in os.supports_fd,
                         "test needs fd support for posix.listdir()")
    def test_listdir_fd(self):
        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        self.addCleanup(posix.close, f)
        self.assertEqual(
            sorted(posix.listdir('.')),
            sorted(posix.listdir(f))
            )
        # Check that the fd offset was reset (issue #13739)
        self.assertEqual(
            sorted(posix.listdir('.')),
            sorted(posix.listdir(f))
            )

    @unittest.skipUnless(hasattr(posix, 'access'), 'test needs posix.access()')
    def test_access(self):
        self.assertTrue(posix.access(os_helper.TESTFN, os.R_OK))

    @unittest.skipUnless(hasattr(posix, 'umask'), 'test needs posix.umask()')
    def test_umask(self):
        old_mask = posix.umask(0)
        self.assertIsInstance(old_mask, int)
        posix.umask(old_mask)

    @unittest.skipUnless(hasattr(posix, 'strerror'),
                         'test needs posix.strerror()')
    def test_strerror(self):
        self.assertTrue(posix.strerror(0))

    @unittest.skipUnless(hasattr(posix, 'pipe'), 'test needs posix.pipe()')
    def test_pipe(self):
        reader, writer = posix.pipe()
        os.close(reader)
        os.close(writer)

    @unittest.skipUnless(hasattr(os, 'pipe2'), "test needs os.pipe2()")
    @support.requires_linux_version(2, 6, 27)
    def test_pipe2(self):
        self.assertRaises(TypeError, os.pipe2, 'DEADBEEF')
        self.assertRaises(TypeError, os.pipe2, 0, 0)

        # try calling with flags = 0, like os.pipe()
        r, w = os.pipe2(0)
        os.close(r)
        os.close(w)

        # test flags
        r, w = os.pipe2(os.O_CLOEXEC|os.O_NONBLOCK)
        self.addCleanup(os.close, r)
        self.addCleanup(os.close, w)
        self.assertFalse(os.get_inheritable(r))
        self.assertFalse(os.get_inheritable(w))
        self.assertFalse(os.get_blocking(r))
        self.assertFalse(os.get_blocking(w))
        # try reading from an empty pipe: this should fail, not block
        self.assertRaises(OSError, os.read, r, 1)
        # try a write big enough to fill-up the pipe: this should either
        # fail or perform a partial write, not block
        try:
            os.write(w, b'x' * support.PIPE_MAX_SIZE)
        except OSError:
            pass

    @support.cpython_only
    @unittest.skipUnless(hasattr(os, 'pipe2'), "test needs os.pipe2()")
    @support.requires_linux_version(2, 6, 27)
    def test_pipe2_c_limits(self):
        # Issue 15989
        import _testcapi
        self.assertRaises(OverflowError, os.pipe2, _testcapi.INT_MAX + 1)
        self.assertRaises(OverflowError, os.pipe2, _testcapi.UINT_MAX + 1)

    @unittest.skipUnless(hasattr(posix, 'utime'), 'test needs posix.utime()')
    def test_utime(self):
        now = time.time()
        posix.utime(os_helper.TESTFN, None)
        self.assertRaises(TypeError, posix.utime,
                          os_helper.TESTFN, (None, None))
        self.assertRaises(TypeError, posix.utime,
                          os_helper.TESTFN, (now, None))
        self.assertRaises(TypeError, posix.utime,
                          os_helper.TESTFN, (None, now))
        posix.utime(os_helper.TESTFN, (int(now), int(now)))
        posix.utime(os_helper.TESTFN, (now, now))

    def _test_chflags_regular_file(self, chflags_func, target_file, **kwargs):
        st = os.stat(target_file)
        self.assertTrue(hasattr(st, 'st_flags'))

        # ZFS returns EOPNOTSUPP when attempting to set flag UF_IMMUTABLE.
        flags = st.st_flags | stat.UF_IMMUTABLE
        try:
            chflags_func(target_file, flags, **kwargs)
        except OSError as err:
            if err.errno != errno.EOPNOTSUPP:
                raise
            msg = 'chflag UF_IMMUTABLE not supported by underlying fs'
            self.skipTest(msg)

        try:
            new_st = os.stat(target_file)
            self.assertEqual(st.st_flags | stat.UF_IMMUTABLE, new_st.st_flags)
            try:
                fd = open(target_file, 'w+')
            except OSError as e:
                self.assertEqual(e.errno, errno.EPERM)
        finally:
            posix.chflags(target_file, st.st_flags)

    @unittest.skipUnless(hasattr(posix, 'chflags'), 'test needs os.chflags()')
    def test_chflags(self):
        self._test_chflags_regular_file(posix.chflags, os_helper.TESTFN)

    @unittest.skipUnless(hasattr(posix, 'lchflags'), 'test needs os.lchflags()')
    def test_lchflags_regular_file(self):
        self._test_chflags_regular_file(posix.lchflags, os_helper.TESTFN)
        self._test_chflags_regular_file(posix.chflags, os_helper.TESTFN,
                                        follow_symlinks=False)

    @unittest.skipUnless(hasattr(posix, 'lchflags'), 'test needs os.lchflags()')
    def test_lchflags_symlink(self):
        testfn_st = os.stat(os_helper.TESTFN)

        self.assertTrue(hasattr(testfn_st, 'st_flags'))

        os.symlink(os_helper.TESTFN, _DUMMY_SYMLINK)
        self.teardown_files.append(_DUMMY_SYMLINK)
        dummy_symlink_st = os.lstat(_DUMMY_SYMLINK)

        def chflags_nofollow(path, flags):
            return posix.chflags(path, flags, follow_symlinks=False)

        for fn in (posix.lchflags, chflags_nofollow):
            # ZFS returns EOPNOTSUPP when attempting to set flag UF_IMMUTABLE.
            flags = dummy_symlink_st.st_flags | stat.UF_IMMUTABLE
            try:
                fn(_DUMMY_SYMLINK, flags)
            except OSError as err:
                if err.errno != errno.EOPNOTSUPP:
                    raise
                msg = 'chflag UF_IMMUTABLE not supported by underlying fs'
                self.skipTest(msg)
            try:
                new_testfn_st = os.stat(os_helper.TESTFN)
                new_dummy_symlink_st = os.lstat(_DUMMY_SYMLINK)

                self.assertEqual(testfn_st.st_flags, new_testfn_st.st_flags)
                self.assertEqual(dummy_symlink_st.st_flags | stat.UF_IMMUTABLE,
                                 new_dummy_symlink_st.st_flags)
            finally:
                fn(_DUMMY_SYMLINK, dummy_symlink_st.st_flags)

    def test_environ(self):
        if os.name == "nt":
            item_type = str
        else:
            item_type = bytes
        for k, v in posix.environ.items():
            self.assertEqual(type(k), item_type)
            self.assertEqual(type(v), item_type)

    def test_putenv(self):
        with self.assertRaises(ValueError):
            os.putenv('FRUIT\0VEGETABLE', 'cabbage')
        with self.assertRaises(ValueError):
            os.putenv(b'FRUIT\0VEGETABLE', b'cabbage')
        with self.assertRaises(ValueError):
            os.putenv('FRUIT', 'orange\0VEGETABLE=cabbage')
        with self.assertRaises(ValueError):
            os.putenv(b'FRUIT', b'orange\0VEGETABLE=cabbage')
        with self.assertRaises(ValueError):
            os.putenv('FRUIT=ORANGE', 'lemon')
        with self.assertRaises(ValueError):
            os.putenv(b'FRUIT=ORANGE', b'lemon')

    @unittest.skipUnless(hasattr(posix, 'getcwd'), 'test needs posix.getcwd()')
    def test_getcwd_long_pathnames(self):
        dirname = 'getcwd-test-directory-0123456789abcdef-01234567890abcdef'
        curdir = os.getcwd()
        base_path = os.path.abspath(os_helper.TESTFN) + '.getcwd'

        try:
            os.mkdir(base_path)
            os.chdir(base_path)
        except:
            #  Just returning nothing instead of the SkipTest exception, because
            #  the test results in Error in that case.  Is that ok?
            #  raise unittest.SkipTest("cannot create directory for testing")
            return

            def _create_and_do_getcwd(dirname, current_path_length = 0):
                try:
                    os.mkdir(dirname)
                except:
                    raise unittest.SkipTest("mkdir cannot create directory sufficiently deep for getcwd test")

                os.chdir(dirname)
                try:
                    os.getcwd()
                    if current_path_length < 1027:
                        _create_and_do_getcwd(dirname, current_path_length + len(dirname) + 1)
                finally:
                    os.chdir('..')
from subprocess import *
import subprocess
import os.path
import os
import sys
import random

os.environ["WORK"]=os.path.expanduser("~/work")
os.environ["CD"]=os.path.expanduser("~/cd")
os.environ["FORMAT"]="squashfs"
os.environ["FS_DIR"]="casper"




def __runcmd(cmd):
    #print cmd
    
    #os.system(cmd)
    return call(cmd, executable="/bin/bash", shell=True)
    #return Popen(cmd, executable="/bin/bash", stdin=PIPE, stdout=PIPE, stderr=PIPE, env=os.environ, shell=True)



    
def copyToNewFS():
    """Copy your installation into the new filesystem """

    cmd1 = "sudo rsync -av --one-file-system --exclude=/proc/* --exclude=/dev/* \
--exclude=/sys/* --exclude=/tmp/* --exclude=/home/* --exclude=/lost+found \
--exclude=/var/tmp/* --exclude=/boot/grub/* --exclude=/root/* \
--exclude=/var/mail/* --exclude=/var/spool/* --exclude=/media/* \
--exclude=/etc/fstab --exclude=/etc/mtab --exclude=/etc/hosts \
--exclude=/etc/timezone --exclude=/etc/shadow* --exclude=/etc/gshadow* \
--exclude=/etc/X11/xorg.conf* --exclude=/etc/gdm/custom.conf \
--exclude=/etc/lightdm/lightdm.conf --exclude=${WORK}/rootfs / ${WORK}/rootfs"
    result1 = __runcmd(cmd1)

    ## If you have a separate boot partition you will have to copy it using the following command
    #cmd2 = "sudo cp -av /boot/* ${WORK}/rootfs/boot"
    #result2 = __runcmd(cmd2)

    ## Copy settings in your home dir:
    ## If you want to preseve your user account settings which are stored in your home directory, you can copy them to ${WORK}/rootfs/etc/skel/. But
    ## first we have to define what files we want to copy. For example I am using xcfe4 as my DE, and it stores all it settings in a directory called
    ## .config in my home directory.
    dirList = os.listdir(os.environ["HOME"])
    hiddenDirFileList = [name for name in dirList if name.startswith(".")]
    hiddenDirOnlyList = [name for name in hiddenDirFileList if os.path.isdir(os.path.join(os.environ["HOME"], name))]
    CONFIG = hiddenDirOnlyList    
    
    ## Now, Copy the CONFIG files using the following command
    os.chdir(os.path.expanduser("~"))

    for dirname in CONFIG:
        cmd3 = "sudo cp -rpv --parents " + dirname + " ${WORK}/rootfs/etc/skel"
        result3 = __runcmd(cmd3)

    ## Make Documents, Downloads, Music, Picutres, Public, Videos directories in /etc/skel
    cmd4 = "cd ${WORK}/rootfs/etc/skel && sudo mkdir Documents Downloads Music Picutres Public Videos"
    result4 = __runcmd(cmd4)

    cmd5 = "cd ~"
    result5 = __runcmd(cmd5)    




def chrootToNewFS():
    """Chroot into the copied system after mounting proc and dev"""

    CHROOT="sudo chroot ${WORK}/rootfs "

    cmd1 = """sudo mount --bind /dev/ ${WORK}/rootfs/dev
sudo mount -t proc proc ${WORK}/rootfs/proc
sudo mount -t sysfs sysfs ${WORK}/rootfs/sys
sudo mount -o bind /run ${WORK}/rootfs/run"""
    result1 = __runcmd(cmd1)



    cmdchroot="""LANG=en_US.UTF-8

apt-get update
apt-get install casper lupin-casper
apt-get install ubiquity ubiquity-frontend-gtk
sudo apt-get install gparted testdisk wipe partimage xfsprogs reiserfsprogs jfsutils ntfs-3g dosfstools mtools

depmod -a $(uname -r)
update-initramfs -u -k $(uname -r)

for i in `cat /etc/passwd | awk -F":" '{print $1}'`
do
uid=`cat /etc/passwd | grep "^${i}:" | awk -F":" '{print $3}'`
[ "$uid" -gt "998" -a "$uid" -ne "65534" ] && userdel --force ${i} 2> /dev/null
done

apt-get clean

find /var/log -regex '.*?[0-9].*?' -exec rm -v {} \;

find /var/log -type f | while read file
do
cat /dev/null | tee $file
done

rm /etc/hostname

exit"""
    
    try:
        fname = "/tmp/chrtnewfs_.sh"
        with open(fname, 'w') as rf:
            rf.write(cmdchroot)
        cmdtmp1 = "sudo mv " + fname + " /home/kiran/work/rootfs/tmp"
        resulttmp1 = __runcmd(cmdtmp1)
        cmdtmp2 = CHROOT + "/bin/bash " + fname
        resulttmp2 = __runcmd(cmdtmp2)
    except Exception as ex:
        print "Exception Occured!", ex
    finally:
        cmdtmp3 = CHROOT + "rm " + fname
        resulttmp3 = __runcmd(cmdtmp3)




def prepareCDDir():
    """Prepare The CD directory tree"""
    
    ## Copy the kernel, the updated initrd and memtest prepared in the chroot
    cmd1 = "export kversion=`cd ${WORK}/rootfs/boot && ls -1 vmlinuz-* | tail -1 | sed 's@vmlinuz-@@'`"
    result1 = __runcmd(cmd1)

    cmd2 = """sudo cp -vp ${WORK}/rootfs/boot/vmlinuz-${kversion} ${CD}/${FS_DIR}/vmlinuz
sudo cp -vp ${WORK}/rootfs/boot/initrd.img-${kversion} ${CD}/${FS_DIR}/initrd.img
sudo cp -vp ${WORK}/rootfs/boot/memtest86+.bin ${CD}/boot"""
    result2 = __runcmd(cmd2)

    ## Generate manifest
    cmd3 = """sudo chroot ${WORK}/rootfs dpkg-query -W --showformat='${Package} ${Version}\n' | sudo tee ${CD}/${FS_DIR}/filesystem.manifest"""
    result3 = __runcmd(cmd3)
    
    cmd4 = """sudo cp -v ${CD}/${FS_DIR}/filesystem.manifest{,-desktop}"""
    result4 = __runcmd(cmd4)

    cmd5 = """REMOVE='ubiquity casper user-setup os-prober libdebian-installer4'
for i in $REMOVE
do
sudo sed -i "/${i}/d" ${CD}/${FS_DIR}/filesystem.manifest-desktop
done"""
    result5 = __runcmd(cmd5)

    ## Unmount bind mounted dirs
    cmd6 = """sudo umount ${WORK}/rootfs/proc
sudo umount ${WORK}/rootfs/sys
sudo umount ${WORK}/rootfs/dev"""
    result6 = __runcmd(cmd6)




def createSquashfs():
    """Convert the directory tree into a squashfs"""
    cmd1 = "sudo mksquashfs ${WORK}/rootfs ${CD}/${FS_DIR}/filesystem.${FORMAT} -noappend"
    result1 = __runcmd(cmd1)

    ## Make filesystem.size
    cmd2 = "echo -n $(sudo du -s --block-size=1 ${WORK}/rootfs | tail -1 | awk '{print $1}') | sudo tee ${CD}/${FS_DIR}/filesystem.size"
    result2 = __runcmd(cmd2)

    ## Calculate MD5
    cmd3 = """find ${CD} -type f -print0 | sudo xargs -0 md5sum | sed "s@${CD}@.@" | grep -v md5sum.txt | sudo tee ${CD}/md5sum.txt"""
    result3 = __runcmd(cmd3)




def createGrubCfg():
    """Make Grub the bootloader of the CD"""

    ##  Make the grub.cfg
    GRUBCFG="""set default="0"
set timeout=10

menuentry "Ubuntu GUI" {
linux /casper/vmlinuz boot=casper quiet splash
initrd /casper/initrd.img
}

menuentry "Ubuntu in safe mode" {
linux /casper/vmlinuz boot=casper xforcevesa quiet splash
initrd /casper/initrd.img
}

menuentry "Ubuntu CLI" {
linux /casper/vmlinuz boot=casper textonly quiet splash
initrd /casper/initrd.img
}

menuentry "Ubuntu GUI persistent mode" {
linux /casper/vmlinuz boot=casper persistent quiet splash
initrd /casper/initrd.img
}

menuentry "Ubuntu GUI from RAM" {
linux /casper/vmlinuz boot=casper toram quiet splash
initrd /casper/initrd.img
}

menuentry "Check Disk for Defects" {
linux /casper/vmlinuz boot=casper integrity-check quiet splash
initrd /casper/initrd.img
}

menuentry "Memory Test" {
linux16 /boot/memtest86+.bin
}

menuentry "Boot from the first hard disk" {
set root=(hd0)
chainloader +1
}"""
    
    tmpfile = "/tmp/tmpmenucfg_.cfg."
    with open(tmpfile, "w") as tmpf:
        tmpf.write(GRUBCFG)
    cmd1 = "cat " + tmpfile + " | " + "sudo tee ${CD}/boot/grub/grub.cfg > /dev/null"
    result1 = __runcmd(cmd1)
    os.remove(tmpfile)
    



def buildCD():
    """Build the CD/DVD"""
    ##Make the ISO file
    cmd = "sudo grub-mkrescue -o " + os.environ["HOME"] + "/live-cd.iso ${CD}"
    result = __runcmd(cmd)




def cleanup():
    """Clean our workspace"""
    cmd = """[ -d "$WORK" ] && rm -r $WORK $CD"""
    result = __runcmd(cmd)



def test():
    cmd = """[ -d "/home/kiran/livecdproj/test" ] && rm -r /home/kiran/livecdproj/test /home/kiran/livecdproj/cdtest"""
    print cmd
    result = __runcmd(cmd)
    
    
    
    
if __name__=="__main__":
    test()
    '''
    copyToNewFS()
    chrootToNewFS()
    prepareCDDir()
    createSquashfs()
    createGrubCfg()
    buildCD()
    '''
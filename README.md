# devops
## Getting Started

### Prerequisites
```
ansible
```

### Installing
```
https://github.com/srekcahrai/devops.git
```

## Running
### Ansible
Run **playbook_user_creation.yml** using hosts file
```
ansible-playbook playbook_user_creation.yml
```

Run **playbook_user_creation.yml** using ssh passing parameters
```
ansible-playbook -i "127.0.0.1," -e "ansible_ssh_port=22 ansible_ssh_user=root" playbook_user_creation.yml
```

Run **playbook_user_creation.yml** using ssh passing parameters and command parameters
```
ansible-playbook -i "127.0.0.1," -e "ansible_ssh_port=22 ansible_ssh_user=root username=devops identity_file=~/devops.pub is_nopasswd=yes is_sudo=yes" ansible/playbook_user_creation.yml
```

import os.path
import csv
from datetime import datetime
from utils import get_ldap_info
from multiprocessing import Pool
import concurrent
from concurrent.futures import ThreadPoolExecutor

# На сколько обрезать ящики
max_count = 100
# Имя csv
csv_name = 'shard_mailbox.csv'
# Количество процессов и тредов
multiprocessing_count = int(os.cpu_count() / 2)
thread_count = multiprocessing_count * 2


def pars_group(members):
    with concurrent.futures.ThreadPoolExecutor(thread_count) as executor:
        members_list = []
        for member in members:
            members_list.append(
                executor.submit(get_ldap_info, f'(&(objectCategory=person)(distinguishedName={member}))',
                                ['sAMAccountName', 'mail']))

        result = []
        for res in concurrent.futures.as_completed(members_list):
            result.append(
                *[item['attributes']['sAMAccountName'] for item in res.result() if item['type'] != 'searchResRef'])

    return ','.join(result)


def save_csv(file_name, shared_dict):
    if os.path.exists(file_name):
        if os.path.exists(file_name.replace('.csv', '_old.csv')):
            os.remove(file_name.replace('.csv', '_old.csv'))
        os.rename(file_name, file_name.replace('.csv', '_old.csv'))

    with open(file_name, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(shared_dict[0].keys()), delimiter=';')
        writer.writeheader()
        while len(shared_dict):
            writer.writerow(shared_dict.pop())


def pars_member_mbx(mail, groups):
    shared_group = {'sharedmailbox': mail.split('@')[0]}
    filter_group = ''
    if len(groups) > 1:
        filter_group += '|'
        for value in groups:
            filter_group += f'(sAMAccountName=*{value}*)'
    else:
        filter_group += f'sAMAccountName=*{groups[0]}*'
    # получаем список групп для ящика
    collection_group = get_ldap_info(
        f'(&(objectCategory=Group)({filter_group})(|(sAMAccountName=*_read)(sAMAccountName=*_edit)(sAMAccountName=*_full)'
        f'(sAMAccountName=*_send)))',
        ['sAMAccountName', 'member'])
    # Чистим генератор
    collection_group = [item['attributes'] for item in collection_group if item['type'] != 'searchResRef']
    # перебираем группы
    for item in collection_group:
        # если группа _суффикс, то парсим членов
        if 'full' in item['sAMAccountName']:
            shared_group['full'] = pars_group(item['member'])
        elif 'edit' in item['sAMAccountName']:
            shared_group['edit'] = pars_group(item['member'])
        elif 'send' in item['sAMAccountName']:
            shared_group['send'] = pars_group(item['member'])
        elif 'read' in item['sAMAccountName']:
            shared_group['read'] = pars_group(item['member'])

    return shared_group


def pars_shared_mbx(shared_dict):
    with Pool(multiprocessing_count) as p:
        return p.starmap(pars_member_mbx, zip(shared_dict.keys(), shared_dict.values()))


if __name__ == "__main__":
    # Получаем список всех ОЯ
    results = get_ldap_info('(&(objectCategory=person)(msExchRecipientTypeDetails=4))',
                            ['displayName', 'sAMAccountName', 'mail'])

    # Парсим результат
    shared_mailboxes = {
        item['attributes']['mail']: list({item['attributes']['displayName'], item['attributes']['sAMAccountName']}) for
        item
        in
        results if item['type'] != 'searchResRef'}
    # обрезаем словарь
    print(len(shared_mailboxes))
    # shared_mailboxes = {key: shared_mailboxes[key] for key in list(shared_mailboxes.keys())[:max_count]}
    start_time = datetime.now()

    # Получаем лист словарей [{оя:'',full:'',send:'',read:'',edit:''},...]
    all_oa = pars_shared_mbx(shared_mailboxes)

    # время выполнения скрипта
    print(f"work time : ,{(datetime.now() - start_time)}")

    # Сохраняем всё в csv
    save_csv(csv_name, all_oa)

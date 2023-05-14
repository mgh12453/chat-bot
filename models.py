from tinydb import TinyDB, Query
import logging
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

MAIN_DIR = os.getcwd()
DATABASE_DIRECTORY = os.path.join(MAIN_DIR, '/db/')

UserIns = {
    'username': '',
    'id': -1,
    'rule': 'student',
    'connection': None
}

ConnectionIns = {
    'teacher': -1,
    'student': -1
}

AdminIns = {
    'id': 1204472487,
    'chat_id': 0,
    'username': 'mmd0dmm'
}

WaitListIns = {
    'chat_id': -1,
    'contacts': []
}

logger.warning('creating models')
User = TinyDB(os.path.join(DATABASE_DIRECTORY, 'user.json'))
Connection = TinyDB(os.path.join(DATABASE_DIRECTORY, 'connection.json'))
Admin = TinyDB(os.path.join(DATABASE_DIRECTORY, 'admin.json'))
WaitList = TinyDB(os.path.join(DATABASE_DIRECTORY, 'wait_list.json'))
User.insert(UserIns)
Connection.insert(ConnectionIns)
Admin.insert(AdminIns)
WaitList.insert(WaitListIns)


def get_or_create_user(id: int, username: str = None, rule: str = None, connection: int = None):
    if User.contains(Query().id == id):
        logger.warning(f'get user {id} from db')
        return User.get(Query().id == id)
    else:
        logger.warning(f'create user {id} in db')
        User.insert({'id': id, 'username': username, 'rule': rule, 'connection': connection})
        return User.get(Query().id == id)


def get_or_create_connection(id: int = None, teacher: int = None, student: int = None):
    if id is not None and Connection.contains(Query().id == id):
        logger.warning(f'get connection {id} from db')
        return Connection.get(Query().doc_id == id)
    elif Connection.contains((Query().teacher == teacher) & (Query().student == student)):
        logger.warning(f'get connection teacher-{teacher} and student-{student} from db')
        return Connection.get((Query().teacher == teacher) & (Query().student == student))
    else:
        logger.warning(f'create connection {teacher}-{student} in db')
        con = Connection.insert({'teacher': teacher, 'student': student})
        User.update({'connection': con}, Query().id == teacher)
        User.update({'connection': con}, Query().id == student)
        return Connection.get((Query().teacher == teacher) & (Query().student == student))


def remove_connection(id: int = None, teacher: int = None, student: int = None):
    if teacher is None or student is None:
        con = Connection.get(doc_id=id)
        teacher, student = con.teacher.id, con.student.id
        Connection.insert({'teacher': teacher, 'student': student})
        User.update({'connection': -1}, Query().id == teacher)
        User.update({'connection': -1}, Query().id == student)
    else:
        Connection.insert({'teacher': teacher, 'student': student})
        User.update({'connection': -1}, Query().id == teacher)
        User.update({'connection': -1}, Query().id == student)
